/**
 * Archie Speech-to-Text (STT) Providers (ESR-STD-v2.4 §7).
 * 
 * Provides:
 * 1. WebSpeechSTTProvider: Production implementation using W3C Web Speech API.
 * 2. MockSTTProvider: Deterministic test implementation for automated tests.
 */

import type { STTCallbacks, STTProvider } from './types.ts';
import { TranscriptAssembler } from './transcriptAssembler.ts';

// Declare Web Speech types for TypeScript
declare global {
  interface Window {
    SpeechRecognition?: any;
    webkitSpeechRecognition?: any;
  }
}

export class WebSpeechSTTProvider implements STTProvider {
  private recognition: any = null;
  private locale: string = 'en-IN';
  private listening: boolean = false;
  private callbacks: STTCallbacks | null = null;
  private assembler: TranscriptAssembler;
  private silenceTimer: any = null;
  private maxDurationTimer: any = null;
  private silenceThresholdMs: number = 1200;
  private maxDurationMs: number = 60000;
  private sessionId: string = '';
  private isExplicitlyStopping: boolean = false;

  constructor(locale: string = 'en-IN', silenceThresholdMs: number = 1200, maxDurationMs: number = 60000) {
    this.locale = locale;
    this.silenceThresholdMs = silenceThresholdMs;
    this.maxDurationMs = maxDurationMs;
    this.assembler = new TranscriptAssembler();
  }

  public isSupported(): boolean {
    if (typeof window === 'undefined') return false;
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  }

  public setLocale(locale: string): void {
    this.locale = locale;
    if (this.recognition) {
      this.recognition.lang = locale;
    }
  }

  public getLocale(): string {
    return this.locale;
  }

  public isListening(): boolean {
    return this.listening;
  }

  public start(callbacks: STTCallbacks): void {
    if (this.listening) {
      this.stop();
    }

    if (!this.isSupported()) {
      callbacks.onError('Web Speech API (SpeechRecognition) is not supported in this browser.');
      return;
    }

    this.callbacks = callbacks;
    this.isExplicitlyStopping = false;
    this.sessionId = `stt-sess-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    this.assembler.reset(this.sessionId);

    const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = new SpeechRecognitionClass();

    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.maxAlternatives = 1;
    this.recognition.lang = this.locale;

    const currentSessionId = this.sessionId;

    this.recognition.onstart = () => {
      if (this.sessionId !== currentSessionId) return;
      this.listening = true;
      this.resetMaxDurationTimer();
    };

    this.recognition.onspeechstart = () => {
      if (this.sessionId !== currentSessionId) return;
      this.callbacks?.onSpeechStart?.();
    };

    this.recognition.onresult = (event: any) => {
      if (this.sessionId !== currentSessionId) return;

      const processed = this.assembler.processEvent(event, currentSessionId);
      if (processed.fullDisplay) {
        this.callbacks?.onInterim(processed.fullDisplay);
      }

      // Reset VAD silence timer on active incoming speech
      this.resetSilenceTimer();
    };

    this.recognition.onerror = (event: any) => {
      if (this.sessionId !== currentSessionId) return;
      const errorMsg = event?.error || 'Speech recognition encountered an unknown error.';
      
      // 'no-speech' or 'aborted' during explicit stop are non-fatal
      if (errorMsg === 'no-speech' || (errorMsg === 'aborted' && this.isExplicitlyStopping)) {
        return;
      }

      this.callbacks?.onError(errorMsg);
    };

    this.recognition.onend = () => {
      if (this.sessionId !== currentSessionId) return;
      this.listening = false;
      this.clearTimers();

      // If stopped with pending transcript, finalize it
      const finalUtterance = this.assembler.finalizeUtterance();
      if (finalUtterance) {
        this.callbacks?.onFinal(finalUtterance);
      }

      this.callbacks?.onEnd();
    };

    try {
      this.recognition.start();
    } catch (err: any) {
      this.listening = false;
      callbacks.onError(err?.message || 'Failed to start speech recognition.');
    }
  }

  public stop(): void {
    this.isExplicitlyStopping = true;
    this.clearTimers();

    if (this.recognition && this.listening) {
      try {
        this.recognition.stop();
      } catch {
        // Ignore if already stopped
      }
    }

    const finalUtterance = this.assembler.finalizeUtterance();
    if (finalUtterance && this.callbacks) {
      this.callbacks.onFinal(finalUtterance);
    }

    this.listening = false;
  }

  /**
   * Diagnostic simulation hook for automated E2E tests (ESR-STD-v2.4 §4).
   * Injects speech recognition events into the active provider callbacks.
   */
  public simulateRecognitionEvent(transcript: string, isFinal: boolean = true): void {
    if (!this.callbacks) {
      console.warn('[WebSpeechSTTProvider] Cannot simulate event: callbacks not registered.');
      return;
    }
    if (isFinal) {
      this.callbacks.onInterim(transcript);
      this.callbacks.onFinal(transcript);
    } else {
      this.callbacks.onInterim(transcript);
    }
  }

  public abort(): void {
    this.isExplicitlyStopping = true;
    this.clearTimers();
    this.sessionId = ''; // Invalidate session to drop pending events

    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch {
        // Ignore
      }
    }
    this.listening = false;
  }

  private resetSilenceTimer(): void {
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
    }

    this.silenceTimer = setTimeout(() => {
      // VAD silence trigger: finalize utterance and stop
      if (this.listening) {
        this.stop();
      }
    }, this.silenceThresholdMs);
  }

  private resetMaxDurationTimer(): void {
    if (this.maxDurationTimer) {
      clearTimeout(this.maxDurationTimer);
    }

    this.maxDurationTimer = setTimeout(() => {
      // Max utterance timeout: stop recording
      if (this.listening) {
        this.stop();
      }
    }, this.maxDurationMs);
  }

  private clearTimers(): void {
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
    if (this.maxDurationTimer) {
      clearTimeout(this.maxDurationTimer);
      this.maxDurationTimer = null;
    }
  }
}

/**
 * Mock STT Provider for headless tests and deterministic simulation.
 */
export class MockSTTProvider implements STTProvider {
  private locale: string = 'en-IN';
  private listening: boolean = false;
  private callbacks: STTCallbacks | null = null;
  public transcriptHistory: string[] = [];

  public isListening(): boolean {
    return this.listening;
  }

  public setLocale(locale: string): void {
    this.locale = locale;
  }

  public getLocale(): string {
    return this.locale;
  }

  public start(callbacks: STTCallbacks): void {
    this.listening = true;
    this.callbacks = callbacks;
  }

  public stop(): void {
    if (!this.listening) return;
    this.listening = false;
    this.callbacks?.onEnd();
  }

  public abort(): void {
    this.listening = false;
  }

  // Test simulation helpers
  public simulateInterim(text: string): void {
    if (this.listening && this.callbacks) {
      this.callbacks.onInterim(text);
    }
  }

  public simulateFinal(text: string): void {
    if (this.listening && this.callbacks) {
      this.transcriptHistory.push(text);
      this.callbacks.onFinal(text);
    }
  }

  public simulateError(error: string): void {
    if (this.callbacks) {
      this.callbacks.onError(error);
    }
  }
}
