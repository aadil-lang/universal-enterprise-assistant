'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { normalizeMarkdown } from '../lib/markdown';

export { normalizeMarkdown };

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  const normalized = normalizeMarkdown(content);

  return (
    <div className="text-sm leading-relaxed text-slate-800 break-words">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Safe link component: only allows http, https, mailto, and relative/anchor links
          a({ href, children, ...props }) {
            const isSafe = href && /^(https?:|mailto:|#|\/)/i.test(href);
            if (!isSafe) {
              return <span>{children}</span>;
            }
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline font-medium"
                {...props}
              >
                {children}
              </a>
            );
          },
          p({ children }) {
            return <p className="my-1.5 leading-relaxed">{children}</p>;
          },
          strong({ children }) {
            return <strong className="font-semibold text-slate-900">{children}</strong>;
          },
          em({ children }) {
            return <em className="italic">{children}</em>;
          },
          ul({ children }) {
            return <ul className="list-disc list-inside space-y-1 my-2 text-slate-800 pl-1">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="list-decimal list-inside space-y-1 my-2 text-slate-800 pl-1">{children}</ol>;
          },
          li({ children }) {
            return <li className="leading-relaxed">{children}</li>;
          },
          h1({ children }) {
            return <h1 className="text-base font-bold text-slate-900 mt-3 mb-1.5 border-b border-slate-200 pb-1">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="text-sm font-bold text-slate-900 mt-2.5 mb-1">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mt-2 mb-1">{children}</h3>;
          },
          pre({ node, children, ...props }: any) {
            return (
              <pre className="p-3 my-2 rounded-xl bg-slate-900 text-slate-100 text-xs font-mono overflow-x-auto" {...props}>
                {children}
              </pre>
            );
          },
          code({ node, className, children, ...props }: any) {
            const isBlock = /language-/.test(className || '') || String(children).includes('\n');
            if (!isBlock) {
              return (
                <code
                  className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-800 text-xs font-mono font-medium border border-slate-200"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-2.5 border border-slate-200 rounded-lg">
                <table className="min-w-full divide-y divide-slate-200 text-xs text-left text-slate-800">
                  {children}
                </table>
              </div>
            );
          },
          thead({ children }) {
            return <thead className="bg-slate-50 font-semibold text-slate-900">{children}</thead>;
          },
          tbody({ children }) {
            return <tbody className="divide-y divide-slate-100 bg-white">{children}</tbody>;
          },
          th({ children }) {
            return <th className="px-3 py-2 text-xs font-semibold text-slate-900">{children}</th>;
          },
          td({ children }) {
            return <td className="px-3 py-2 text-xs text-slate-700">{children}</td>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-4 border-blue-500 pl-3 my-2 italic text-slate-600 bg-blue-50/40 py-1 rounded-r">
                {children}
              </blockquote>
            );
          },
          hr() {
            return <hr className="my-3 border-slate-200" />;
          },
        }}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  );
};
