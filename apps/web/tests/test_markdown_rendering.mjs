/**
 * Focused Regression Test Suite for Markdown Formatting & Escaped Asterisks.
 * Covers requirements 1-10:
 * 1. Normal bold Markdown renders as bold (<strong>).
 * 2. Italic Markdown renders correctly (<em>).
 * 3. Bullet and numbered lists render correctly (<ul>, <ol>, <li>).
 * 4. Headings render correctly (<h1>, <h2>, <h3>).
 * 5. Inline and fenced code render correctly (<code>, <pre>).
 * 6. Normal links work safely (<a> with https).
 * 7. Unsafe HTML and javascript: URLs are not executed.
 * 8. Literal \*\* is normalized without breaking legitimate backslashes.
 * 9. Policy citations ([Doc, Section]) remain visible and intact.
 * 10. Plain text responses without Markdown continue to render correctly.
 * Plus verification of the exact reproduction response.
 */

import assert from 'node:assert';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { normalizeMarkdown } from '../lib/markdown.ts';

console.log('--- Starting Markdown Formatting Regression Test Suite ---');

const safeComponents = {
  a({ href, children, ...props }) {
    const isSafe = href && /^(https?:|mailto:|#|\/)/i.test(href);
    if (!isSafe) {
      return React.createElement('span', null, children);
    }
    return React.createElement('a', {
      href,
      target: '_blank',
      rel: 'noopener noreferrer',
      className: 'text-blue-600 hover:text-blue-800 underline font-medium',
      ...props
    }, children);
  },
  strong({ children }) {
    return React.createElement('strong', { className: 'font-semibold text-slate-900' }, children);
  },
  em({ children }) {
    return React.createElement('em', { className: 'italic' }, children);
  },
  p({ children }) {
    return React.createElement('p', { className: 'my-1.5 leading-relaxed' }, children);
  },
  ul({ children }) {
    return React.createElement('ul', { className: 'list-disc list-inside space-y-1 my-2 text-slate-800 pl-1' }, children);
  },
  ol({ children }) {
    return React.createElement('ol', { className: 'list-decimal list-inside space-y-1 my-2 text-slate-800 pl-1' }, children);
  },
  li({ children }) {
    return React.createElement('li', { className: 'leading-relaxed' }, children);
  },
  h1({ children }) {
    return React.createElement('h1', { className: 'text-base font-bold' }, children);
  },
  h2({ children }) {
    return React.createElement('h2', { className: 'text-sm font-bold' }, children);
  },
  pre({ node, children, ...props }) {
    return React.createElement('pre', { className: 'code-block' }, children);
  },
  code({ node, className, children, ...props }) {
    const isBlock = /language-/.test(className || '') || String(children).includes('\n');
    if (!isBlock) {
      return React.createElement('code', { className: 'inline-code' }, children);
    }
    return React.createElement('code', { className }, children);
  }
};

function renderMarkdown(content) {
  const normalized = normalizeMarkdown(content);
  return renderToStaticMarkup(
    React.createElement(ReactMarkdown, {
      remarkPlugins: [remarkGfm],
      components: safeComponents,
    }, normalized)
  );
}

// 1. Normal bold Markdown renders as <strong>
{
  const html = renderMarkdown('This is **bold text** in chat.');
  assert(html.includes('<strong class="font-semibold text-slate-900">bold text</strong>'));
  console.log('✓ Test 1: Bold Markdown renders as <strong>.');
}

// 2. Italic Markdown renders as <em>
{
  const html = renderMarkdown('This is *italic text* and _more italic_.');
  assert(html.includes('<em class="italic">italic text</em>'));
  assert(html.includes('<em class="italic">more italic</em>'));
  console.log('✓ Test 2: Italic Markdown renders as <em>.');
}

// 3. Bullet and numbered lists render correctly
{
  const bulletHtml = renderMarkdown('- First item\n- Second item');
  assert(bulletHtml.includes('<ul') && bulletHtml.includes('<li class="leading-relaxed">First item</li>'));

  const numHtml = renderMarkdown('1. First step\n2. Second step');
  assert(numHtml.includes('<ol') && numHtml.includes('<li class="leading-relaxed">First step</li>'));
  console.log('✓ Test 3: Bullet and numbered lists render correctly.');
}

// 4. Headings render correctly
{
  const html = renderMarkdown('# Main Heading\n## Subheading');
  assert(html.includes('<h1 class="text-base font-bold">Main Heading</h1>'));
  assert(html.includes('<h2 class="text-sm font-bold">Subheading</h2>'));
  console.log('✓ Test 4: Headings render correctly.');
}

// 5. Inline and fenced code render correctly
{
  const inlineHtml = renderMarkdown('Run `npm run dev` to start.');
  assert(inlineHtml.includes('<code class="inline-code">npm run dev</code>'));

  const fencedHtml = renderMarkdown('```\nconst x = 42;\n```');
  assert(fencedHtml.includes('<pre class="code-block"><code>const x = 42;'));
  console.log('✓ Test 5: Inline and fenced code render correctly.');
}

// 6. Normal links work safely
{
  const html = renderMarkdown('Visit [Acme Portal](https://portal.acme.com) today.');
  assert(html.includes('<a href="https://portal.acme.com" target="_blank" rel="noopener noreferrer"'));
  assert(html.includes('Acme Portal</a>'));
  console.log('✓ Test 6: Normal links render with safe target and rel.');
}

// 7. Unsafe HTML and javascript: URLs are not executed
{
  const scriptHtml = renderMarkdown('<script>alert("xss")</script>');
  assert(!scriptHtml.includes('<script>alert("xss")</script>'));

  const jsLinkHtml = renderMarkdown('[Malicious](javascript:alert(1))');
  assert(!jsLinkHtml.includes('href="javascript:'));
  assert(jsLinkHtml.includes('<span>Malicious</span>'));
  console.log('✓ Test 7: Unsafe HTML and javascript: URLs are stripped/sanitized.');
}

// 8. Literal \\*\\* is normalized without breaking legitimate backslashes
{
  const escapedHtml = renderMarkdown('Here is \\*\\*escaped bold\\*\\* text.');
  assert(escapedHtml.includes('<strong class="font-semibold text-slate-900">escaped bold</strong>'));
  assert(!escapedHtml.includes('\\*\\*'));

  // Legitimate backslashes preserved
  const pathText = 'File is at C:\\Users\\HP\\Documents\\report.docx';
  assert(normalizeMarkdown(pathText) === pathText);
  const regexText = 'Regex pattern \\d+ and \\w+';
  assert(normalizeMarkdown(regexText) === regexText);
  console.log('✓ Test 8: Literal \\*\\* normalized without breaking legitimate backslashes.');
}

// 9. Policy citations remain visible
{
  const citationText = 'Employees are entitled to 18 days of leave [Acme Leave Policy, 1. Purpose and Scope].';
  const html = renderMarkdown(citationText);
  assert(html.includes('[Acme Leave Policy, 1. Purpose and Scope]'));
  console.log('✓ Test 9: Policy citations remain intact and visible.');
}

// 10. Existing chat responses without Markdown continue to render correctly
{
  const plainText = 'I am an enterprise HR & IT assistant. I can only assist with company policies and your employee records.';
  const html = renderMarkdown(plainText);
  assert(html.includes('<p class="my-1.5 leading-relaxed">I am an enterprise HR &amp; IT assistant.'));
  console.log('✓ Test 10: Plain text responses without Markdown render as clean paragraphs.');
}

// 11. Exact reproduction response verification
{
  const exactRepro = `Based on company policy and your employee records, here is the information regarding your sick leave:

- **Company Policy Entitlement:** Employees accrue sick leave at a rate of 10 days per calendar year. Unused sick leave can be carried over into subsequent years up to a maximum rollover cap of 5 days.
- **Your Personal Sick Leave Record:** According to your employee records for fiscal year 2026, you have accrued 10.0 days, used 2.0 days, and currently have **8.0 available days** of sick leave.`;

  const html = renderMarkdown(exactRepro);

  // Assert both labels are rendered inside <strong>
  assert(html.includes('<strong class="font-semibold text-slate-900">Company Policy Entitlement:</strong>'));
  assert(html.includes('<strong class="font-semibold text-slate-900">Your Personal Sick Leave Record:</strong>'));

  // Assert "8.0 available days" is rendered inside <strong>
  assert(html.includes('<strong class="font-semibold text-slate-900">8.0 available days</strong>'));

  // Assert no escaping backslashes or raw asterisks appear
  assert(!html.includes('\\*\\*'));
  assert(!html.includes('\\*'));
  assert(!html.includes('**'));

  console.log('✓ Test 11: Exact reproduction response rendered with bold labels and 8.0 available days!');
}

console.log('--- All 11 Focused Markdown Regression Tests Passed ---');
