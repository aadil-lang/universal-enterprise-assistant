/**
 * Archie Wake-Word Detection Utility (ESR-STD-v2.4 §4).
 * 
 * Supports local browser-based phrase detection:
 * - Detects "Hey Archie" (case-insensitive, normalized).
 * - Also recognizes common variants like "Hi Archie", "Archie".
 * - Extracts any trailing query if user says "Hey Archie, what is my leave balance?" in one breath.
 */

export interface WakeWordResult {
  detected: boolean;
  matchedPhrase?: string;
  remainderQuery?: string;
}

export class WakeWordDetector {
  private wakePhrases: string[];

  constructor(customPhrases?: string[]) {
    this.wakePhrases = customPhrases || [
      'hey archie',
      'hi archie',
      'ok archie',
      'hello archie',
      'archie',
    ];
  }

  /**
   * Evaluates input transcript against wake phrase targets.
   */
  public detect(transcript: string): WakeWordResult {
    if (!transcript || typeof transcript !== 'string') {
      return { detected: false };
    }

    // Normalize: lowercase, remove punctuation except whitespace
    const clean = transcript
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    if (!clean) {
      return { detected: false };
    }

    for (const phrase of this.wakePhrases) {
      // Check exact match or start of utterance
      if (clean === phrase) {
        return { detected: true, matchedPhrase: phrase, remainderQuery: '' };
      }

      if (clean.startsWith(`${phrase} `)) {
        const remainder = clean.slice(phrase.length).trim();
        return {
          detected: true,
          matchedPhrase: phrase,
          remainderQuery: remainder,
        };
      }

      // Also check if wake phrase appears inside the utterance
      const index = clean.indexOf(phrase);
      if (index !== -1) {
        const remainder = clean.slice(index + phrase.length).trim();
        return {
          detected: true,
          matchedPhrase: phrase,
          remainderQuery: remainder,
        };
      }
    }

    return { detected: false };
  }
}
