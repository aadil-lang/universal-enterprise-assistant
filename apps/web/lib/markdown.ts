/**
 * Normalizes assistant response text prior to Markdown rendering:
 * - Unescapes literal backslash-escaped Markdown markers (e.g. `\*\*` -> `**`, `\_` -> `_`)
 *   that may be emitted by upstream LLM synthesis,
 *   while strictly preserving legitimate backslashes (e.g. Windows file paths `C:\Users\..`, math, regex).
 */
export function normalizeMarkdown(text: string): string {
  if (!text) return '';
  return text.replace(/\\+(\*|_)/g, '$1');
}
