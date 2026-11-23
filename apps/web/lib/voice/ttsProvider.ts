/**
 * Archie Speech Synthesis (TTS) Providers (ESR-STD-v2.4 §6, §10).
 * 
 * Provides:
 * 1. WebSpeechTTSProvider: Uses browser-native SpeechSynthesis with intelligent female en-IN voice selection.
 * 2. MockTTSProvider: Deterministic test implementation for automated tests.
 */

import type { TTSCallbacks, TTSProvider } from './types.ts';

// Known female voice keywords across Windows, macOS, Android, and Chromium
const FEMALE_VOICE_KEYWORDS = [
  'heera',
  'neerja',
  'swara',
  'aditi',
  'veena',
  'priya',
  'kalpana',
  'zira',
  'samantha',
  'karen',
  'moira',
  'victoria',
  'female',
  'woman',
  'girl',
];

export class WebSpeechTTSProvider implements TTSProvider {
  private locale: string = 'en-IN';
  private selectedVoice: SpeechSynthesisVoice | null = null;
  private currentUtteranceId: number = 0;
  private speaking: boolean = false;
  public onVoicesChanged?: (voices: SpeechSynthesisVoice[]) => void;

  constructor(locale: string = 'en-IN') {
    this.locale = locale;
    this.initializeVoices();
  }

  public isSupported(): boolean {
    if (typeof window === 'undefined') return false;
    return 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
  }

  public setLocale(locale: string): void {
    this.locale = locale;
    this.selectBestVoice();
  }

  public getLocale(): string {
    return this.locale;
  }

  public isSpeaking(): boolean {
    return this.speaking;
  }

  public getSelectedVoice(): SpeechSynthesisVoice | null {
    if (!this.selectedVoice) {
      this.selectBestVoice();
    }
    return this.selectedVoice;
  }

  public getAvailableVoices(): SpeechSynthesisVoice[] {
    if (!this.isSupported()) return [];
    try {
      return window.speechSynthesis.getVoices() || [];
    } catch {
      return [];
    }
  }

  private initializeVoices(): void {
    if (!this.isSupported()) return;

    this.selectBestVoice();

    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = () => {
        const voices = this.getAvailableVoices();
        this.selectBestVoice();
        this.onVoicesChanged?.(voices);
      };
    }
  }

  /**
   * Evaluates available voices and selects the optimal voice following the ESR-STD-v2.4 ranking:
   * 1. Female Indian English voice (en-IN + female name)
   * 2. Any Indian English voice (en-IN)
   * 3. Female English voice (en-* + female name)
   * 4. Any English voice (en-*)
   * 5. System default
   */
  public selectBestVoice(): SpeechSynthesisVoice | null {
    const voices = this.getAvailableVoices();
    if (!voices || voices.length === 0) {
      return null;
    }

    const targetLang = this.locale.toLowerCase().replace('_', '-');

    // 1. Female Indian English
    const femaleIn = voices.find((v) => {
      const vLang = (v.lang || '').toLowerCase().replace('_', '-');
      const vName = (v.name || '').toLowerCase();
      const isTargetLang = vLang.startsWith(targetLang) || vLang.includes('en-in');
      const isFemale = FEMALE_VOICE_KEYWORDS.some((kw) => vName.includes(kw));
      return isTargetLang && isFemale;
    });
    if (femaleIn) {
      this.selectedVoice = femaleIn;
      return femaleIn;
    }

    // 2. Any Indian English
    const anyIn = voices.find((v) => {
      const vLang = (v.lang || '').toLowerCase().replace('_', '-');
      return vLang.startsWith(targetLang) || vLang.includes('en-in');
    });
    if (anyIn) {
      this.selectedVoice = anyIn;
      return anyIn;
    }

    // 3. Female English (any region)
    const femaleEn = voices.find((v) => {
      const vLang = (v.lang || '').toLowerCase();
      const vName = (v.name || '').toLowerCase();
      return vLang.startsWith('en') && FEMALE_VOICE_KEYWORDS.some((kw) => vName.includes(kw));
    });
    if (femaleEn) {
      this.selectedVoice = femaleEn;
      return femaleEn;
    }

    // 4. Any English voice
    const anyEn = voices.find((v) => (v.lang || '').toLowerCase().startsWith('en'));
    if (anyEn) {
      this.selectedVoice = anyEn;
      return anyEn;
    }

    // 5. Default fallback
    this.selectedVoice = voices[0] || null;
    return this.selectedVoice;
  }

  public speak(text: string, callbacks?: TTSCallbacks): void {
    if (!text || !text.trim()) {
      callbacks?.onEnd?.();
      return;
    }

    if (!this.isSupported()) {
      callbacks?.onError?.('SpeechSynthesis is not supported in this browser.');
      return;
    }

    // Cancel any previous speech
    this.stop();

    const utteranceId = ++this.currentUtteranceId;
    this.speaking = true;

    try {
      const utterance = new SpeechSynthesisUtterance(text.trim());
      const voice = this.getSelectedVoice();
      if (voice) {
        utterance.voice = voice;
      }
      utterance.lang = voice?.lang || this.locale;
      utterance.rate = 1.0;
      utterance.pitch = 1.05; // Slightly elevated for natural warm conversational delivery
      utterance.volume = 1.0;

      utterance.onstart = () => {
        if (this.currentUtteranceId !== utteranceId) return;
        this.speaking = true;
        callbacks?.onStart?.();
      };

      utterance.onend = () => {
        if (this.currentUtteranceId !== utteranceId) return;
        this.speaking = false;
        callbacks?.onEnd?.();
      };

      utterance.onerror = (e) => {
        if (this.currentUtteranceId !== utteranceId) return;
        this.speaking = false;
        callbacks?.onError?.(e?.error || 'Speech synthesis error occurred.');
      };

      window.speechSynthesis.speak(utterance);
    } catch (err: any) {
      this.speaking = false;
      callbacks?.onError?.(err?.message || 'Failed to synthesize speech.');
    }
  }

  public stop(): void {
    this.currentUtteranceId++; // Invalidate stale callbacks
    this.speaking = false;

    if (this.isSupported()) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // Ignore
      }
    }
  }
}

/**
 * Mock TTS Provider for headless testing and validation.
 */
export class MockTTSProvider implements TTSProvider {
  private locale: string = 'en-IN';
  private speaking: boolean = false;
  public spokenTexts: string[] = [];
  public selectedVoice: any = {
    name: 'Microsoft Heera - English (India)',
    lang: 'en-IN',
    default: true,
    localService: true,
    voiceURI: 'Microsoft Heera',
  };

  public isSpeaking(): boolean {
    return this.speaking;
  }

  public setLocale(locale: string): void {
    this.locale = locale;
  }

  public getLocale(): string {
    return this.locale;
  }

  public getAvailableVoices(): SpeechSynthesisVoice[] {
    return [
      this.selectedVoice as SpeechSynthesisVoice,
      { name: 'Microsoft David - English (United States)', lang: 'en-US' } as SpeechSynthesisVoice,
      { name: 'Microsoft Zira - English (United States)', lang: 'en-US' } as SpeechSynthesisVoice,
    ];
  }

  public getSelectedVoice(): SpeechSynthesisVoice | null {
    return this.selectedVoice as SpeechSynthesisVoice;
  }

  public speak(text: string, callbacks?: TTSCallbacks): void {
    this.stop();
    this.speaking = true;
    this.spokenTexts.push(text);
    callbacks?.onStart?.();

    // Simulate completion
    setTimeout(() => {
      if (this.speaking) {
        this.speaking = false;
        callbacks?.onEnd?.();
      }
    }, 10);
  }

  public stop(): void {
    this.speaking = false;
  }
}
