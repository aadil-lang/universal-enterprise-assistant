/**
 * Natural Conversational Speech Response Formatter (ESR-STD-v2.4 §4, §10).
 * 
 * Transforms authoritative LangGraph / assistant written Markdown responses
 * into warm, natural, human-sounding spoken language for Archie:
 * - Conversational phrasing and natural contractions ("You've got", "I found", "I just need").
 * - Strips internal state, tool metadata, JSON, debug blocks, and technical citation lines.
 * - Suppresses raw IDs (conf-..., hashes, UUIDs), technical URLs, and Markdown syntax.
 * - Converts ISO dates into natural spoken formats (e.g. "December 22nd, 2026").
 * - Summarizes Markdown tables conversationally without reading raw pipe delimiters.
 * - Preserves exact numbers, monetary amounts, names, and critical request statuses.
 * - Enforces factual consistency: falls back safely to clean verbatim speech if numbers or statuses are altered.
 * - Never replaces or alters the complete written Markdown answer displayed in the chat interface.
 */

export interface SpeechFormattingOptions {
  conversationalize?: boolean;
  suppressCitations?: boolean;
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

function getOrdinalSuffix(day: number): string {
  if (day > 3 && day < 21) return `${day}th`;
  switch (day % 10) {
    case 1: return `${day}st`;
    case 2: return `${day}nd`;
    case 3: return `${day}rd`;
    default: return `${day}th`;
  }
}

export class SpeechResponseFormatter {
  /**
   * Main entry point to format authoritative written Markdown into natural spoken language.
   */
  public format(markdown: string, options: SpeechFormattingOptions = {}): string {
    if (!markdown || typeof markdown !== 'string') return '';

    const opts = {
      conversationalize: true,
      suppressCitations: true,
      ...options,
    };

    // Step 1: Base sanitization (clean debug artifacts, code blocks, tables, links)
    const baseCleaned = this.cleanBaseMarkdown(markdown);

    if (!opts.conversationalize) {
      return baseCleaned;
    }

    // Step 2: Apply natural conversational transformation
    const conversational = this.transformToConversational(baseCleaned, opts);

    // Step 3: Factual consistency check
    // Ensure all critical numbers and status guarantees are preserved
    if (!this.validateFactualConsistency(baseCleaned, conversational)) {
      console.warn('[SpeechResponseFormatter] Factual consistency check failed; falling back to clean faithful text.');
      return baseCleaned;
    }

    return conversational;
  }

  /**
   * Sanitizes Markdown, code blocks, tables, and internal artifacts.
   */
  public cleanBaseMarkdown(markdown: string): string {
    let text = markdown;

    // 1. Remove hidden / debug / internal artifacts and HTML comments
    text = text.replace(/<!--[\s\S]*?-->/g, '');
    text = text.replace(/```(?:json|xml|yaml|sql)[\s\S]*?```/gi, '');
    text = text.replace(/\{[\s\S]*?"(?:mcp_tools_used|retrieval_decision|tool_call)"[\s\S]*?\}/gi, '');

    // 2. Remove fenced code blocks
    text = text.replace(/```[\s\S]*?```/g, ' [code details available on screen] ');

    // 3. Convert Markdown tables to natural conversational summaries
    text = this.convertTablesForSpeech(text);

    // 4. Clean Markdown links [label](url) -> "label"
    text = text.replace(/\[([^\]]+)\]\((?:https?:\/\/[^\s)]+|#[^\s)]+)\)/g, '$1');
    text = text.replace(/https?:\/\/[^\s]+/g, 'link on screen');

    // 5. Technical citation metadata lines removal (e.g. *Source: Policy.pdf*, (Section 4.1))
    text = text.replace(/^\s*(?:\*|_)*\s*(?:source|references?|citations?|policy document):\s*.*$/gim, '');
    text = text.replace(/\b(?:source|references?|citations?):\s*[\w\s.-]+\.(?:pdf|docx|md|txt)[^\n.]*/gi, '');
    text = text.replace(/\([\w\s.-]+\.(?:pdf|docx|md|txt)[^)]*\)/gi, '');
    text = text.replace(/\[\d+\]/g, '');
    text = text.replace(/\[[\w\s.-]+\.(?:pdf|docx|md|txt)\]/gi, '');

    // 6. Raw tokens, hashes, and UUIDs
    text = text.replace(/\bconf-[a-f0-9]{16,64}\b/gi, '');
    text = text.replace(/\b[a-f0-9]{32,64}\b/gi, '');

    // 7. Inline code `value` -> value
    text = text.replace(/`([^`]+)`/g, '$1');

    // 8. Bold and italics formatting
    text = text.replace(/\*\*\*([^*]+)\*\*\*/g, '$1');
    text = text.replace(/\*\*([^*]+)\*\*/g, '$1');
    text = text.replace(/\*([^*]+)\*/g, '$1');
    text = text.replace(/___([^_]+)___/g, '$1');
    text = text.replace(/__([^_]+)__/g, '$1');
    text = text.replace(/_([^_]+)_/g, '$1');

    // 9. Headings (# Title, ## Subtitle)
    text = text.replace(/^#{1,6}\s*(.+)$/gm, '$1.');

    // 10. Bullet lists and numbered lists (- item, * item, 1. item)
    text = text.replace(/^\s*[-*+]\s+/gm, ' ');
    text = text.replace(/^\s*\d+\.\s+/gm, ' ');

    // 11. Horizontal rules (---, ***)
    text = text.replace(/^[-*_]{3,}$/gm, ' ');

    // 12. Currency normalization
    text = text.replace(/\$([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)/g, '$1 dollars');
    text = text.replace(/₹([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)/g, '$1 rupees');
    text = text.replace(/€([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)/g, '$1 euros');
    text = text.replace(/£([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)/g, '$1 pounds');

    // 13. Corporate abbreviations phonetics
    text = text.replace(/\bIT\b/g, 'I.T.');
    text = text.replace(/\bHR\b/g, 'H.R.');
    text = text.replace(/\bAPI\b/g, 'A.P.I.');
    text = text.replace(/\bUI\b/g, 'U.I.');
    text = text.replace(/\bMCP\b/g, 'M.C.P.');

    // 14. Clean whitespace & punctuation
    text = text.replace(/\s*([,?!])\s*/g, '$1 ');
    text = text.replace(/([a-z])\.([A-Z])/g, '$1. $2');
    text = text.replace(/\.{2,}/g, '.');
    text = text.replace(/\s+/g, ' ').trim();

    return text;
  }

  /**
   * Converts formal corporate prose into natural conversational speech with contractions and friendly cadence.
   */
  public transformToConversational(text: string, options: SpeechFormattingOptions): string {
    let s = text;

    // A. Security confirmation refusal phrasing
    if (/require explicit confirmation using the ['"]Confirm Submission['"] button/i.test(s)) {
      return "For your security and corporate compliance, you'll need to tap the Confirm Submission button on your screen to complete this.";
    }

    // B. ISO date pronunciation (e.g. 2026-12-10 to 2026-12-12 -> December 10th to 12th, 2026)
    s = this.convertIsoDates(s);

    // C. Natural phrase conversions (Section 4 examples)
    // "Your available annual leave balance is 8 days." -> "You've got 8 days of annual leave available."
    s = s.replace(/Your available annual leave balance is\s+(\d+(?:\.\d+)?)\s+days?\./gi, "You've got $1 days of annual leave available.");
    // "You currently have 8.0 days of annual leave available" -> "You've got 8.0 days of annual leave available"
    s = s.replace(/You currently have\s+(\d+(?:\.\d+)?)\s+days?\s+of\s+annual\s+leave\s+available/gi, "You've got $1 days of annual leave available");
    // "I have identified three relevant policies." -> "I found three policies that might help."
    s = s.replace(/I have identified\s+(\w+|\d+)\s+relevant\s+policies\.?/gi, "I found $1 policies that might help.");
    // "Please provide the required information." -> "Sure. I just need a couple of details first."
    s = s.replace(/Please provide the required information\.?/gi, "Sure. I just need a couple of details first.");
    // "Your request has been submitted successfully." -> "All done. Your request has been submitted."
    s = s.replace(/Your request has been submitted successfully\.?/gi, "All done. Your request has been submitted.");
    // "The requested equipment is currently pending approval." -> "Your equipment request is still waiting for approval."
    s = s.replace(/The requested equipment is currently pending approval\.?/gi, "Your equipment request is still waiting for approval.");
    s = s.replace(/\bis currently pending approval\b/gi, "is still waiting for approval");

    // D. Transaction and status notifications
    s = s.replace(/Please review and confirm your ([\w\s]+) request:?/gi, "I've set up your $1 request. Please take a look on your screen and confirm.");
    s = s.replace(/Action Confirmed & Executed\.?/gi, "All done! Your request has been confirmed and officially executed.");
    s = s.replace(/Submission Successful!?/gi, "All done! Your request has been officially recorded.");

    // E. Apply friendly English contractions
    s = this.applyContractions(s);

    // F. Clean up repetitive spacing and trailing punctuation
    s = s.replace(/\s+/g, ' ').trim();

    return s;
  }

  /**
   * Applies natural English contractions while preserving capitalization.
   */
  public applyContractions(text: string): string {
    let s = text;
    const contractions: [RegExp, string][] = [
      [/\byou have\b/gi, "you've"],
      [/\bI have\b/g, "I've"],
      [/\bi have\b/g, "I've"],
      [/\bwe have\b/gi, "we've"],
      [/\bthey have\b/gi, "they've"],
      [/\bdo not\b/gi, "don't"],
      [/\bcannot\b/gi, "can't"],
      [/\bcan not\b/gi, "can't"],
      [/\bcould not\b/gi, "couldn't"],
      [/\bwould not\b/gi, "wouldn't"],
      [/\bshould not\b/gi, "shouldn't"],
      [/\bis not\b/gi, "isn't"],
      [/\bare not\b/gi, "aren't"],
      [/\bwill not\b/gi, "won't"],
      [/\bit is\b/gi, "it's"],
      [/\bthat is\b/gi, "that's"],
      [/\bthere is\b/gi, "there's"],
      [/\byou will\b/gi, "you'll"],
      [/\bwe will\b/gi, "we'll"],
      [/\bI will\b/g, "I'll"],
    ];

    for (const [pattern, replacement] of contractions) {
      s = s.replace(pattern, (match) => {
        if (match[0] === match[0].toUpperCase()) {
          return replacement[0].toUpperCase() + replacement.slice(1);
        }
        return replacement;
      });
    }

    return s;
  }

  /**
   * Converts ISO dates into natural spoken phrasing.
   */
  public convertIsoDates(text: string): string {
    // ISO date ranges: 2026-12-10 to 2026-12-12
    let s = text.replace(/\b(\d{4})-(\d{2})-(\d{2})\s*(?:to|-|through)\s*(\d{4})-(\d{2})-(\d{2})\b/g, (match, y1, m1, d1, y2, m2, d2) => {
      const month1 = MONTH_NAMES[parseInt(m1, 10) - 1];
      const day1 = getOrdinalSuffix(parseInt(d1, 10));
      const month2 = MONTH_NAMES[parseInt(m2, 10) - 1];
      const day2 = getOrdinalSuffix(parseInt(d2, 10));
      if (y1 === y2 && m1 === m2) {
        return `${month1} ${day1} to ${day2}, ${y1}`;
      }
      if (y1 === y2) {
        return `${month1} ${day1} to ${month2} ${day2}, ${y1}`;
      }
      return `${month1} ${day1}, ${y1} to ${month2} ${day2}, ${y2}`;
    });

    // Single ISO date: 2026-12-10
    s = s.replace(/\b(\d{4})-(\d{2})-(\d{2})\b/g, (match, y, m, d) => {
      const month = MONTH_NAMES[parseInt(m, 10) - 1];
      const day = getOrdinalSuffix(parseInt(d, 10));
      return `${month} ${day}, ${y}`;
    });

    return s;
  }

  /**
   * Detects Markdown tables and transforms them into conversational spoken summaries.
   */
  public convertTablesForSpeech(input: string): string {
    const tableRegex = /(\|[^\n]+\|\r?\n)((?:\|:?[-]+:?)+\|(?:\r?\n|$))((?:\|[^\n]+\|\r?\n?)+)/g;

    return input.replace(tableRegex, (match, headerRow, separator, bodyRows) => {
      try {
        const headers = headerRow
          .split('|')
          .map((h: string) => h.trim())
          .filter((h: string) => h.length > 0);

        const rows = bodyRows
          .trim()
          .split(/\r?\n/)
          .map((row: string) =>
            row
              .split('|')
              .map((c: string) => c.trim())
              .filter((c: string) => c.length > 0)
          )
          .filter((row: string[]) => row.length > 0);

        if (rows.length === 0) return '';

        // Short table (1-3 rows): speak concisely
        if (rows.length <= 3) {
          const spokenRows = rows.map((cols: string[]) => {
            return cols
              .map((val: string, idx: number) => {
                const header = headers[idx] || `Item ${idx + 1}`;
                return `${header}: ${val}`;
              })
              .join(', ');
          });
          return `. Here are the details: ${spokenRows.join('. ')}. `;
        }

        // Long table (> 3 rows): summarize count and invite on-screen viewing
        return `. There is a detailed table on your screen with ${rows.length} entries for ${headers.join(', ')}. `;
      } catch {
        return ' [Details shown in table on screen] ';
      }
    });
  }

  /**
   * Verifies that all numbers, monetary figures, and critical status keywords are faithfully preserved.
   */
  public validateFactualConsistency(original: string, spoken: string): boolean {
    // 1. Normalize dates first so date components (e.g. month 12 -> "December") are properly accounted for
    const normOrig = this.convertIsoDates(original);
    const origNums = this.extractNumericValues(normOrig);
    const spokenNums = this.extractNumericValues(spoken);

    for (const num of origNums) {
      if (!spokenNums.includes(num)) {
        return false;
      }
    }

    // 2. Validate critical status words
    const statuses = ['submitted', 'approved', 'rejected', 'cancelled', 'refused'];
    for (const st of statuses) {
      const inOrig = new RegExp(`\\b${st}\\b`, 'i').test(original);
      const inSpoken = new RegExp(`\\b${st}\\b`, 'i').test(spoken);
      if (inOrig && !inSpoken) {
        return false;
      }
    }

    return true;
  }

  private extractNumericValues(str: string): string[] {
    const matches = str.match(/\b\d+(?:\.\d+)?\b/g);
    return matches ? matches.map((n) => parseFloat(n).toString()) : [];
  }
}

/**
 * Convenience wrapper maintaining backward compatibility.
 */
export function formatForSpeech(markdown: string, options?: SpeechFormattingOptions): string {
  const formatter = new SpeechResponseFormatter();
  return formatter.format(markdown, options);
}
