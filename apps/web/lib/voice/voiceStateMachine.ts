/**
 * Archie Voice Session State Machine Coordinator (ESR-STD-v2.4 §14).
 * 
 * Implements deterministic lifecycle:
 * DISABLED
 *   -> WAKE_WORD_LISTENING
 *   -> GREETING
 *   -> ACTIVE_LISTENING
 *   -> FINALIZING
 *   -> PROCESSING
 *   -> SPEAKING
 *   -> ACTIVE_LISTENING (continuous conversation)
 *   -> INACTIVITY_TIMEOUT
 *   -> WAKE_WORD_LISTENING
 * 
 * Supports:
 * - Manual interruption (stops speech immediately on mic click)
 * - Manual Done / Cancel controls
 * - Stop-speaking control
 * - Teardown on logout, session expiration, and unmount
 */

import {
  DEFAULT_VOICE_CONFIG,
  VoiceSessionState,
} from './types.ts';
import type {
  STTProvider,
  TTSProvider,
  VoiceConfig,
  ArchieUserProfile,
} from './types.ts';
import { GreetingService } from './greetingService.ts';
import { WakeWordDetector } from './wakeWordDetector.ts';
import { formatForSpeech } from './speechFormatter.ts';

export interface StateMachineCallbacks {
  onStateChange: (state: VoiceSessionState) => void;
  onLiveTranscript: (text: string) => void;
  onSubmitUtterance: (text: string) => Promise<string | void>;
  onError: (error: string) => void;
}

export class VoiceStateMachine {
  private state: VoiceSessionState = VoiceSessionState.DISABLED;
  private stt: STTProvider;
  private tts: TTSProvider;
  private greetingService: GreetingService;
  private wakeDetector: WakeWordDetector;
  private config: VoiceConfig;
  private callbacks: StateMachineCallbacks;
  private userProfile?: ArchieUserProfile | null;

  private inactivityTimer: any = null;
  private liveTranscript: string = '';
  private isDestroyed: boolean = false;

  constructor(
    stt: STTProvider,
    tts: TTSProvider,
    callbacks: StateMachineCallbacks,
    config: Partial<VoiceConfig> = {},
    userProfile?: ArchieUserProfile | null
  ) {
    this.stt = stt;
    this.tts = tts;
    this.callbacks = callbacks;
    this.config = { ...DEFAULT_VOICE_CONFIG, ...config };
    this.userProfile = userProfile;
    this.greetingService = new GreetingService();
    this.wakeDetector = new WakeWordDetector([this.config.wakePhrase]);
  }

  public getState(): VoiceSessionState {
    return this.state;
  }

  public getLiveTranscript(): string {
    return this.liveTranscript;
  }

  public setUserProfile(profile?: ArchieUserProfile | null): void {
    this.userProfile = profile;
  }

  /**
   * Enables voice mode and enters wake-word listening.
   */
  public enableVoiceMode(): void {
    if (this.state !== VoiceSessionState.DISABLED && this.state !== VoiceSessionState.ERROR) {
      return;
    }
    this.greetingService.resetSession();
    this.transitionTo(VoiceSessionState.WAKE_WORD_LISTENING);
    this.startWakeWordListening();
  }

  /**
   * Disables voice mode and completely cleans up all audio capture/synthesis.
   */
  public disableVoiceMode(): void {
    this.cleanup();
    this.transitionTo(VoiceSessionState.DISABLED);
  }

  /**
   * Manual activation of microphone (fallback / instant talk / barge-in).
   */
  public manualActivateMic(): void {
    if (this.state === VoiceSessionState.DISABLED) {
      this.enableVoiceMode();
    }

    // If currently speaking, interrupt immediately
    if (this.state === VoiceSessionState.SPEAKING) {
      this.tts.stop();
      this.transitionTo(VoiceSessionState.INTERRUPTED);
    }

    this.startActiveListening();
  }

  /**
   * Manual Done button pressed by employee.
   */
  public manualDone(): void {
    if (this.state !== VoiceSessionState.ACTIVE_LISTENING) return;

    this.transitionTo(VoiceSessionState.FINALIZING);
    this.stt.stop(); // Triggers onFinal callback
  }

  /**
   * Manual Cancel button pressed by employee.
   */
  public manualCancel(): void {
    this.clearInactivityTimer();
    this.stt.abort();
    this.liveTranscript = '';
    this.callbacks.onLiveTranscript('');

    // Return to wake-word listening
    this.transitionTo(VoiceSessionState.WAKE_WORD_LISTENING);
    this.startWakeWordListening();
  }

  /**
   * Stop speaking button pressed by employee.
   */
  public stopSpeaking(): void {
    if (this.state === VoiceSessionState.SPEAKING || this.state === VoiceSessionState.GREETING) {
      this.tts.stop();
      this.transitionTo(VoiceSessionState.ACTIVE_LISTENING);
      this.startActiveListening();
    }
  }

  /**
   * Speaks the assistant's answer and then returns to ACTIVE_LISTENING.
   */
  public async speakAnswer(rawText: string): Promise<void> {
    if (this.state === VoiceSessionState.DISABLED || this.isDestroyed) return;

    const formatted = formatForSpeech(rawText);
    if (!formatted) {
      this.transitionTo(VoiceSessionState.ACTIVE_LISTENING);
      this.startActiveListening();
      return;
    }

    this.transitionTo(VoiceSessionState.SPEAKING);

    this.tts.speak(formatted, {
      onEnd: () => {
        if (this.state === VoiceSessionState.SPEAKING && !this.isDestroyed) {
          // Continuous conversation: return to active listening without requiring wake phrase
          this.transitionTo(VoiceSessionState.ACTIVE_LISTENING);
          this.startActiveListening();
        }
      },
      onError: (err) => {
        console.warn('Speech synthesis notification:', err);
        if (this.state === VoiceSessionState.SPEAKING && !this.isDestroyed) {
          this.transitionTo(VoiceSessionState.ACTIVE_LISTENING);
          this.startActiveListening();
        }
      },
    });
  }

  /**
   * Starts listening in wake-word detection mode.
   */
  private startWakeWordListening(): void {
    this.clearInactivityTimer();
    this.liveTranscript = '';
    this.callbacks.onLiveTranscript('');

    this.stt.start({
      onInterim: (text) => {
        this.liveTranscript = text;
        this.callbacks.onLiveTranscript(text);
        this.checkWakeWord(text);
      },
      onFinal: (text) => {
        this.liveTranscript = text;
        this.callbacks.onLiveTranscript(text);
        this.checkWakeWord(text);
      },
      onError: (err) => {
        console.warn('Wake word STT error:', err);
        // In wake-word mode, restart listening unless permanently failing
        if (this.state === VoiceSessionState.WAKE_WORD_LISTENING && !this.isDestroyed) {
          setTimeout(() => {
            if (this.state === VoiceSessionState.WAKE_WORD_LISTENING && !this.isDestroyed) {
              this.startWakeWordListening();
            }
          }, 1000);
        }
      },
      onEnd: () => {
        // If STT stops while still in wake-word listening, restart it
        if (this.state === VoiceSessionState.WAKE_WORD_LISTENING && !this.isDestroyed) {
          this.startWakeWordListening();
        }
      },
    });
  }

  /**
   * Checks if transcript contains wake phrase "Hey Archie".
   */
  private checkWakeWord(text: string): void {
    if (this.state !== VoiceSessionState.WAKE_WORD_LISTENING) return;

    const result = this.wakeDetector.detect(text);
    if (result.detected) {
      // Stop wake word listening
      this.stt.stop();
      this.handleWakeWordTriggered(result.remainderQuery);
    }
  }

  /**
   * Handles successful detection of "Hey Archie".
   */
  private handleWakeWordTriggered(remainderQuery?: string): void {
    if (this.greetingService.shouldGreet()) {
      // Transition to GREETING and speak personalized greeting
      this.transitionTo(VoiceSessionState.GREETING);
      const greetingText = this.greetingService.generateGreeting(this.userProfile);
      this.greetingService.markGreeted();

      this.tts.speak(greetingText, {
        onEnd: () => {
          if (this.state === VoiceSessionState.GREETING && !this.isDestroyed) {
            if (remainderQuery && remainderQuery.trim().length > 0) {
              // User asked a question in the same breath
              this.submitQuestion(remainderQuery.trim());
            } else {
              this.transitionTo(VoiceSessionState.ACTIVE_LISTENING);
              this.startActiveListening();
            }
          }
        },
        onError: () => {
          if (this.state === VoiceSessionState.GREETING && !this.isDestroyed) {
            this.transitionTo(VoiceSessionState.ACTIVE_LISTENING);
            this.startActiveListening();
          }
        },
      });
    } else {
      // Already greeted earlier in this session
      if (remainderQuery && remainderQuery.trim().length > 0) {
        this.submitQuestion(remainderQuery.trim());
      } else {
        this.transitionTo(VoiceSessionState.ACTIVE_LISTENING);
        this.startActiveListening();
      }
    }
  }

  /**
   * Starts active listening for employee's question or follow-up.
   */
  private startActiveListening(): void {
    this.clearInactivityTimer();
    this.liveTranscript = '';
    this.callbacks.onLiveTranscript('');
    this.transitionTo(VoiceSessionState.ACTIVE_LISTENING);

    // Set inactivity timeout: if no speech for inactivityTimeoutMs, return to wake word
    this.resetInactivityTimer();

    this.stt.start({
      onSpeechStart: () => {
        this.clearInactivityTimer();
      },
      onInterim: (text) => {
        this.clearInactivityTimer();
        this.liveTranscript = text;
        this.callbacks.onLiveTranscript(text);
      },
      onFinal: (text) => {
        this.clearInactivityTimer();
        this.liveTranscript = text;
        this.callbacks.onLiveTranscript(text);
        if (text.trim()) {
          this.submitQuestion(text.trim());
        } else {
          this.resetInactivityTimer();
        }
      },
      onError: (err) => {
        console.warn('Active listening STT error:', err);
        this.callbacks.onError(err);
        this.resetInactivityTimer();
      },
      onEnd: () => {
        if (this.state === VoiceSessionState.ACTIVE_LISTENING) {
          // If ended with no final text submitted, start inactivity timer
          this.resetInactivityTimer();
        }
      },
    });
  }

  /**
   * Submits finalized utterance to the backend Chat API.
   */
  private async submitQuestion(question: string): Promise<void> {
    if (!question || this.isDestroyed) return;

    this.clearInactivityTimer();
    this.transitionTo(VoiceSessionState.PROCESSING);

    try {
      const responseAnswer = await this.callbacks.onSubmitUtterance(question);
      if (responseAnswer && typeof responseAnswer === 'string') {
        await this.speakAnswer(responseAnswer);
      } else {
        // If no direct string returned, return to active listening
        this.transitionTo(VoiceSessionState.ACTIVE_LISTENING);
        this.startActiveListening();
      }
    } catch (err: any) {
      console.error('Failed to submit question via voice:', err);
      this.callbacks.onError(err?.message || 'Failed to process voice query.');
      this.transitionTo(VoiceSessionState.ACTIVE_LISTENING);
      this.startActiveListening();
    }
  }

  private resetInactivityTimer(): void {
    this.clearInactivityTimer();
    this.inactivityTimer = setTimeout(() => {
      if (this.state === VoiceSessionState.ACTIVE_LISTENING && !this.isDestroyed) {
        // Return to wake-word listening
        this.stt.stop();
        this.transitionTo(VoiceSessionState.WAKE_WORD_LISTENING);
        this.startWakeWordListening();
      }
    }, this.config.inactivityTimeoutMs);
  }

  private clearInactivityTimer(): void {
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
      this.inactivityTimer = null;
    }
  }

  private transitionTo(newState: VoiceSessionState): void {
    if (this.state === newState) return;
    this.state = newState;
    this.callbacks.onStateChange(newState);
  }

  public cleanup(): void {
    this.isDestroyed = true;
    this.clearInactivityTimer();
    this.stt.abort();
    this.tts.stop();
    this.liveTranscript = '';
    this.greetingService.resetSession();
  }
}
