'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Radio,
  Check,
  X,
  AlertCircle,
  Sparkles,
  Square,
  Shield,
} from 'lucide-react';
import {
  VoiceSessionState,
  WebSpeechSTTProvider,
  WebSpeechTTSProvider,
  VoiceStateMachine,
  ArchieUserProfile,
} from '../lib/voice';

interface ArchieVoiceAssistantProps {
  user: ArchieUserProfile | null;
  onSubmitUtterance: (text: string) => Promise<string | void>;
  isProcessingQuery?: boolean;
}

export const ArchieVoiceAssistant: React.FC<ArchieVoiceAssistantProps> = ({
  user,
  onSubmitUtterance,
  isProcessingQuery = false,
}) => {
  const [voiceState, setVoiceState] = useState<VoiceSessionState>(VoiceSessionState.DISABLED);
  const [liveTranscript, setLiveTranscript] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState<boolean>(true);
  const [selectedVoiceName, setSelectedVoiceName] = useState<string>('Female (en-IN)');
  const [showPrivacyNotice, setShowPrivacyNotice] = useState<boolean>(false);

  const stateMachineRef = useRef<VoiceStateMachine | null>(null);
  const sttProviderRef = useRef<WebSpeechSTTProvider | null>(null);
  const ttsProviderRef = useRef<WebSpeechTTSProvider | null>(null);

  // Initialize providers
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const stt = new WebSpeechSTTProvider('en-IN', 650, 60000);
    const tts = new WebSpeechTTSProvider('en-IN');

    sttProviderRef.current = stt;
    ttsProviderRef.current = tts;

    const supported = stt.isSupported();
    setIsSupported(supported);

    const voice = tts.getSelectedVoice();
    if (voice) {
      setSelectedVoiceName(voice.name);
    }
    tts.onVoicesChanged = () => {
      const v = tts.getSelectedVoice();
      if (v) setSelectedVoiceName(v.name);
    };

    const sm = new VoiceStateMachine(
      stt,
      tts,
      {
        onStateChange: (state) => {
          setVoiceState(state);
          if (state !== VoiceSessionState.ERROR) {
            setErrorMessage(null);
          }
        },
        onLiveTranscript: (text) => {
          setLiveTranscript(text);
        },
        onSubmitUtterance: async (text) => {
          return await onSubmitUtterance(text);
        },
        onError: (err) => {
          setErrorMessage(err);
        },
      },
      {
        wakePhrase: 'hey archie',
        inactivityTimeoutMs: 25000,
        defaultLocale: 'en-IN',
      },
      user
    );

    stateMachineRef.current = sm;

    // Expose diagnostic inspection hooks for automated test harnesses (ESR-STD-v2.4 §4)
    (window as any).__ARCHIE_STT__ = stt;
    (window as any).__ARCHIE_TTS__ = tts;
    (window as any).__ARCHIE_STATE_MACHINE__ = sm;

    return () => {
      sm.cleanup();
      delete (window as any).__ARCHIE_STT__;
      delete (window as any).__ARCHIE_TTS__;
      delete (window as any).__ARCHIE_STATE_MACHINE__;
    };
  }, []);

  // Update employee profile in state machine when user changes or logs in/out
  useEffect(() => {
    if (stateMachineRef.current) {
      stateMachineRef.current.setUserProfile(user);
    }
    // Clean up voice session if user logs out
    if (!user && stateMachineRef.current) {
      stateMachineRef.current.disableVoiceMode();
    }
  }, [user]);

  // Sync processing state if parent is processing
  useEffect(() => {
    if (isProcessingQuery && voiceState === VoiceSessionState.ACTIVE_LISTENING) {
      setVoiceState(VoiceSessionState.PROCESSING);
    }
  }, [isProcessingQuery, voiceState]);

  const handleToggleVoiceMode = useCallback(() => {
    if (!stateMachineRef.current) return;

    if (voiceState === VoiceSessionState.DISABLED) {
      setErrorMessage(null);
      stateMachineRef.current.enableVoiceMode();
    } else {
      stateMachineRef.current.disableVoiceMode();
      setLiveTranscript('');
      setErrorMessage(null);
    }
  }, [voiceState]);

  const handleMicClick = useCallback(() => {
    if (!stateMachineRef.current) return;
    stateMachineRef.current.manualActivateMic();
  }, []);

  const handleDone = useCallback(() => {
    if (!stateMachineRef.current) return;
    stateMachineRef.current.manualDone();
  }, []);

  const handleCancel = useCallback(() => {
    if (!stateMachineRef.current) return;
    stateMachineRef.current.manualCancel();
    setLiveTranscript('');
  }, []);

  const handleStopSpeaking = useCallback(() => {
    if (!stateMachineRef.current) return;
    stateMachineRef.current.stopSpeaking();
  }, []);

  if (!isSupported) {
    return (
      <div className="bg-amber-50 border-b border-amber-200 px-6 py-2 flex items-center justify-between text-xs text-amber-800">
        <div className="flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
          <span>
            Archie voice mode requires a browser supporting Web Speech API (e.g. Chrome, Edge). Text chat remains fully available.
          </span>
        </div>
      </div>
    );
  }

  const isVoiceEnabled = voiceState !== VoiceSessionState.DISABLED;

  return (
    <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white border-b border-indigo-800/40 px-4 py-2.5 transition-all shadow-md">
      <div className="flex flex-wrap items-center justify-between gap-3 max-w-6xl mx-auto">
        {/* Left: Archie Presence & Status Badge */}
        <div className="flex items-center space-x-3">
          <div className="relative">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs shadow-md transition-all ${
                isVoiceEnabled
                  ? voiceState === VoiceSessionState.ACTIVE_LISTENING
                    ? 'bg-rose-500 ring-4 ring-rose-400/30 animate-pulse'
                    : voiceState === VoiceSessionState.SPEAKING
                    ? 'bg-emerald-500 ring-4 ring-emerald-400/30'
                    : voiceState === VoiceSessionState.PROCESSING
                    ? 'bg-amber-500 animate-spin'
                    : 'bg-indigo-600 ring-2 ring-indigo-400/40'
                  : 'bg-slate-700 opacity-60'
              }`}
            >
              {voiceState === VoiceSessionState.ACTIVE_LISTENING ? (
                <Radio className="w-4 h-4 animate-ping text-white" />
              ) : voiceState === VoiceSessionState.SPEAKING ? (
                <Volume2 className="w-4 h-4 text-white" />
              ) : (
                <Sparkles className="w-4 h-4 text-white" />
              )}
            </div>
            {isVoiceEnabled && (
              <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border border-slate-900" />
            )}
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-xs tracking-tight text-white flex items-center gap-1">
                Archie
                <span className="text-[10px] font-normal text-indigo-300">
                  (Voice Assistant • en-IN)
                </span>
              </span>

              {/* Status Pill */}
              <span
                className={`text-[10px] font-medium px-2 py-0.5 rounded-full border transition-all ${
                  voiceState === VoiceSessionState.DISABLED
                    ? 'bg-slate-800/80 text-slate-400 border-slate-700'
                    : voiceState === VoiceSessionState.WAKE_WORD_LISTENING
                    ? 'bg-blue-950/80 text-blue-300 border-blue-700/60'
                    : voiceState === VoiceSessionState.GREETING
                    ? 'bg-purple-950/80 text-purple-200 border-purple-700/60'
                    : voiceState === VoiceSessionState.ACTIVE_LISTENING
                    ? 'bg-rose-950/90 text-rose-200 border-rose-600 animate-pulse'
                    : voiceState === VoiceSessionState.FINALIZING
                    ? 'bg-indigo-950/80 text-indigo-200 border-indigo-700'
                    : voiceState === VoiceSessionState.PROCESSING
                    ? 'bg-amber-950/80 text-amber-200 border-amber-700'
                    : voiceState === VoiceSessionState.SPEAKING
                    ? 'bg-emerald-950/90 text-emerald-200 border-emerald-600'
                    : 'bg-rose-950 text-rose-300 border-rose-700'
                }`}
              >
                {voiceState === VoiceSessionState.DISABLED && 'Voice Mode Off'}
                {voiceState === VoiceSessionState.WAKE_WORD_LISTENING && 'Waiting for "Hey Archie"'}
                {voiceState === VoiceSessionState.GREETING && 'Greeting...'}
                {voiceState === VoiceSessionState.ACTIVE_LISTENING && 'Listening...'}
                {voiceState === VoiceSessionState.FINALIZING && 'Finalizing...'}
                {voiceState === VoiceSessionState.PROCESSING && 'Thinking...'}
                {voiceState === VoiceSessionState.SPEAKING && 'Archie Speaking...'}
                {voiceState === VoiceSessionState.INTERRUPTED && 'Interrupted'}
                {voiceState === VoiceSessionState.ERROR && 'Voice Error'}
              </span>
            </div>

            {/* Subtitle / Tip */}
            <p className="text-[10px] text-slate-400">
              {voiceState === VoiceSessionState.DISABLED
                ? 'Enable voice mode to talk to Archie using "Hey Archie" or microphone button.'
                : voiceState === VoiceSessionState.WAKE_WORD_LISTENING
                ? 'Say "Hey Archie" or click the microphone to speak anytime.'
                : voiceState === VoiceSessionState.ACTIVE_LISTENING
                ? 'Speak your question naturally. Silence will auto-submit.'
                : voiceState === VoiceSessionState.SPEAKING
                ? 'Click microphone or stop speaking to interrupt.'
                : 'Processing authenticated request through enterprise LangGraph workflow.'}
            </p>
          </div>
        </div>

        {/* Center: Live Transcript Bubble */}
        {isVoiceEnabled && liveTranscript && (
          <div className="flex-1 max-w-md mx-2 px-3 py-1 bg-indigo-950/70 border border-indigo-500/40 rounded-xl text-xs text-indigo-100 flex items-center space-x-2 truncate shadow-inner">
            <Radio className="w-3.5 h-3.5 text-rose-400 flex-shrink-0 animate-pulse" />
            <span className="font-mono text-[11px] truncate">&ldquo;{liveTranscript}&rdquo;</span>
          </div>
        )}

        {/* Right: Controls */}
        <div className="flex items-center space-x-2">
          {/* Active Speaking Control: Stop Speaking */}
          {(voiceState === VoiceSessionState.SPEAKING || voiceState === VoiceSessionState.GREETING) && (
            <button
              onClick={handleStopSpeaking}
              className="flex items-center space-x-1 px-2.5 py-1 text-xs font-semibold text-rose-200 bg-rose-900/60 hover:bg-rose-800 border border-rose-700 rounded-lg transition-colors shadow-sm"
              title="Stop speaking"
            >
              <VolumeX className="w-3.5 h-3.5" />
              <span>Stop Speaking</span>
            </button>
          )}

          {/* Active Listening Controls: Done & Cancel */}
          {voiceState === VoiceSessionState.ACTIVE_LISTENING && (
            <div className="flex items-center space-x-1.5">
              <button
                onClick={handleDone}
                className="flex items-center space-x-1 px-2.5 py-1 text-xs font-semibold text-emerald-200 bg-emerald-900/60 hover:bg-emerald-800 border border-emerald-700 rounded-lg transition-colors shadow-sm cursor-pointer"
                title="Finish speaking and submit"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Done</span>
              </button>
              <button
                onClick={handleCancel}
                className="flex items-center space-x-1 px-2 py-1 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg transition-colors cursor-pointer"
                title="Discard speech"
              >
                <X className="w-3.5 h-3.5" />
                <span>Cancel</span>
              </button>
            </div>
          )}

          {/* Manual Mic Activation Button (Available whenever voice is enabled) */}
          {isVoiceEnabled && (
            <button
              onClick={handleMicClick}
              className={`p-2 rounded-xl transition-all shadow-sm flex items-center justify-center cursor-pointer ${
                voiceState === VoiceSessionState.ACTIVE_LISTENING
                  ? 'bg-rose-600 text-white ring-2 ring-rose-400 animate-pulse'
                  : 'bg-indigo-700/80 hover:bg-indigo-600 text-white border border-indigo-500/50'
              }`}
              title={
                voiceState === VoiceSessionState.ACTIVE_LISTENING
                  ? 'Archie is listening...'
                  : 'Click to start speaking directly (or say "Hey Archie")'
              }
            >
              <Mic className="w-4 h-4" />
            </button>
          )}

          {/* Voice Mode Enable/Disable Switch */}
          <button
            onClick={handleToggleVoiceMode}
            className={`flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded-xl border transition-all cursor-pointer ${
              isVoiceEnabled
                ? 'bg-indigo-600 text-white border-indigo-400 hover:bg-indigo-700 shadow-sm'
                : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700 hover:text-white'
            }`}
            title={isVoiceEnabled ? 'Turn off Archie voice mode' : 'Enable Archie voice mode'}
          >
            {isVoiceEnabled ? (
              <>
                <Mic className="w-3.5 h-3.5 text-indigo-200" />
                <span>Voice Enabled</span>
              </>
            ) : (
              <>
                <MicOff className="w-3.5 h-3.5 text-slate-400" />
                <span>Enable Voice</span>
              </>
            )}
          </button>

          {/* Privacy & Audio Security Disclosure Button */}
          <button
            id="archie-privacy-btn"
            onClick={() => setShowPrivacyNotice((prev) => !prev)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors border border-slate-700/60 cursor-pointer"
            title="Archie Voice Privacy & Security Disclosures"
            aria-label="Archie Voice Privacy Notice"
          >
            <Shield className="w-3.5 h-3.5 text-indigo-400" />
          </button>
        </div>
      </div>

      {/* Voice Privacy & Vendor Processing Disclosure (ESR-STD-v2.4 §4) */}
      {showPrivacyNotice && (
        <div
          id="archie-privacy-modal"
          className="mt-2 bg-slate-900 border border-indigo-500/40 rounded-xl p-3 text-xs text-slate-300 shadow-xl"
        >
          <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
            <span className="font-semibold text-white flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-indigo-400" />
              Archie Voice Privacy &amp; Audio Disclosure
            </span>
            <button
              onClick={() => setShowPrivacyNotice(false)}
              className="text-slate-400 hover:text-white font-bold px-1 cursor-pointer"
            >
              ×
            </button>
          </div>
          <ul className="space-y-1.5 text-[11px] text-slate-300 list-disc list-inside">
            <li>
              <strong>No Raw Audio Persistence:</strong> The application does not intentionally persist raw microphone recordings.
            </li>
            <li>
              <strong>No Backend Audio Uploads:</strong> The application does not directly upload raw audio to its own backend; only transcribed text is transmitted to authenticated chat APIs.
            </li>
            <li>
              <strong>Browser Vendor Speech Recognition:</strong> Browser-provided speech recognition (Web Speech API) may process audio through browser-vendor cloud services depending on the browser and its configuration.
            </li>
            <li>
              <strong>Explicit Opt-In &amp; Mic Permission:</strong> Voice mode is strictly opt-in and requires explicit browser microphone permissions.
            </li>
            <li>
              <strong>Text Fallback:</strong> Users can disable voice mode anytime and interact exclusively via standard text chat.
            </li>
          </ul>
        </div>
      )}

      {/* Error Banner if STT/TTS fails */}
      {errorMessage && (
        <div className="mt-1.5 bg-rose-950/80 border border-rose-800 text-rose-200 px-4 py-1.5 rounded-lg text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
            <span>Voice Notice: {errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-rose-400 hover:text-white font-bold ml-2"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
};
