/**
 * Dedicated Transcript Assembly Utility for Archie Voice Assistant.
 * 
 * Requirements (ESR-STD-v2.4 §7.1):
 * - Display interim transcripts as the employee speaks.
 * - Submit only finalized transcript content.
 * - Correctly process resultIndex.
 * - Respect each recognition result's isFinal property.
 * - Reconcile interim and final text without duplicating prefixes.
 * - Preserve legitimate repeated words.
 * - Prevent stale events from modifying a new session.
 * - Prevent duplicate submission of finalized utterances.
 * - Handle recognition restarts without losing valid final transcript content.
 */

export interface SpeechRecognitionResultLike {
  isFinal: boolean;
  length: number;
  [index: number]: { transcript: string; confidence: number };
}

export interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: SpeechRecognitionResultLike;
  };
}

export class TranscriptAssembler {
  private sessionId: string;
  private finalizedSegments: string[] = [];
  private currentInterim: string = '';
  private submittedFinals: Set<string> = new Set();
  private hasSubmittedCurrentCycle: boolean = false;

  constructor(sessionId?: string) {
    this.sessionId = sessionId || `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  }

  public getSessionId(): string {
    return this.sessionId;
  }

  public reset(newSessionId?: string): void {
    this.sessionId = newSessionId || `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    this.finalizedSegments = [];
    this.currentInterim = '';
    this.hasSubmittedCurrentCycle = false;
  }

  /**
   * Process incoming SpeechRecognitionEvent.
   * Returns current combined display transcript (finalized + interim).
   */
  public processEvent(event: SpeechRecognitionEventLike, eventSessionId?: string): {
    fullDisplay: string;
    interim: string;
    finalText: string;
    isCycleFinal: boolean;
  } {
    // Drop events from a stale session
    if (eventSessionId && eventSessionId !== this.sessionId) {
      return {
        fullDisplay: this.getFullDisplay(),
        interim: this.currentInterim,
        finalText: this.getFinalText(),
        isCycleFinal: false,
      };
    }

    let newlyFinalized: string[] = [];
    let activeInterim = '';

    const results = event.results;
    const startIndex = typeof event.resultIndex === 'number' ? event.resultIndex : 0;

    for (let i = startIndex; i < results.length; i++) {
      const result = results[i];
      if (!result || result.length === 0) continue;

      const transcript = (result[0]?.transcript || '').trim();
      if (!transcript) continue;

      if (result.isFinal) {
        newlyFinalized.push(transcript);
      } else {
        activeInterim = activeInterim ? `${activeInterim} ${transcript}` : transcript;
      }
    }

    // Append newly finalized chunks with duplicate prefix reconciliation
    for (const chunk of newlyFinalized) {
      this.appendFinalChunk(chunk);
    }

    this.currentInterim = activeInterim;

    return {
      fullDisplay: this.getFullDisplay(),
      interim: this.currentInterim,
      finalText: this.getFinalText(),
      isCycleFinal: newlyFinalized.length > 0 && !activeInterim,
    };
  }

  /**
   * Adds finalized chunk, ensuring we don't accidentally duplicate an identical prefix
   * when the engine re-emits a finalized hypothesis from resultIndex 0,
   * while preserving legitimate repeated words (e.g. "very very" or "no no").
   */
  public appendFinalChunk(chunk: string): void {
    const trimmed = chunk.trim();
    if (!trimmed) return;

    // Check if the engine re-emitted the whole combined sentence
    const existingCombined = this.finalizedSegments.join(' ').trim();
    if (existingCombined && trimmed.startsWith(existingCombined)) {
      // The new chunk is a superset of what we have (e.g. engine re-emitted from index 0)
      const remainder = trimmed.slice(existingCombined.length).trim();
      if (remainder) {
        this.finalizedSegments = [existingCombined, remainder];
      }
      return;
    }

    this.finalizedSegments.push(trimmed);
  }

  public getFinalText(): string {
    return this.finalizedSegments.join(' ').trim();
  }

  public getFullDisplay(): string {
    const finalPart = this.getFinalText();
    const interimPart = this.currentInterim.trim();

    if (finalPart && interimPart) {
      return `${finalPart} ${interimPart}`;
    }
    return finalPart || interimPart || '';
  }

  /**
   * Finalizes the current utterance cycle and returns the text to be submitted.
   * If there is pending interim text that wasn't marked isFinal before stopping,
   * it gets committed as final.
   * Returns empty string if already submitted or nothing was transcribed.
   */
  public finalizeUtterance(): string {
    if (this.hasSubmittedCurrentCycle) {
      return '';
    }

    // If there is leftover interim text, commit it to final
    if (this.currentInterim.trim()) {
      this.appendFinalChunk(this.currentInterim.trim());
      this.currentInterim = '';
    }

    const finalResult = this.getFinalText().trim();
    if (!finalResult) {
      return '';
    }

    this.hasSubmittedCurrentCycle = true;
    return finalResult;
  }

  public hasSubmitted(): boolean {
    return this.hasSubmittedCurrentCycle;
  }
}
