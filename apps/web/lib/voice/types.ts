/**
 * Archie Voice Assistant — Type Definitions and Interfaces.
 * Follows ESR-STD-v2.4 and W3C Web Speech API specifications.
 */

export const VoiceSessionState = {
  DISABLED: 'DISABLED',
  WAKE_WORD_LISTENING: 'WAKE_WORD_LISTENING',
  GREETING: 'GREETING',
  ACTIVE_LISTENING: 'ACTIVE_LISTENING',
  FINALIZING: 'FINALIZING',
  PROCESSING: 'PROCESSING',
  SPEAKING: 'SPEAKING',
  INTERRUPTED: 'INTERRUPTED',
  ERROR: 'ERROR',
} as const;

export type VoiceSessionState = typeof VoiceSessionState[keyof typeof VoiceSessionState];

export interface VoiceConfig {
  silenceThresholdMs: number;
  maxUtteranceDurationMs: number;
  inactivityTimeoutMs: number;
  defaultLocale: string;
  wakePhrase: string;
}

export const DEFAULT_VOICE_CONFIG: VoiceConfig = {
  silenceThresholdMs: 1200,
  maxUtteranceDurationMs: 60000,
  inactivityTimeoutMs: 25000,
  defaultLocale: 'en-IN',
  wakePhrase: 'hey archie',
};

export interface STTCallbacks {
  onInterim: (text: string) => void;
  onFinal: (text: string) => void;
  onError: (error: string) => void;
  onEnd: () => void;
  onSpeechStart?: () => void;
}

export interface STTProvider {
  start(callbacks: STTCallbacks): void;
  stop(): void;
  abort(): void;
  isListening(): boolean;
  setLocale(locale: string): void;
  getLocale(): string;
}

export interface TTSCallbacks {
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (error: string) => void;
}

export interface TTSProvider {
  speak(text: string, callbacks?: TTSCallbacks): void;
  stop(): void;
  isSpeaking(): boolean;
  getAvailableVoices(): SpeechSynthesisVoice[];
  getSelectedVoice(): SpeechSynthesisVoice | null;
  setLocale(locale: string): void;
  getLocale(): string;
  onVoicesChanged?: (voices: SpeechSynthesisVoice[]) => void;
}

export interface ArchieUserProfile {
  first_name?: string;
  last_name?: string;
  preferred_name?: string;
  employee_number?: string;
  role?: string;
}
