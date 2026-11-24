'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api, ChatCitation, ConfirmationPrompt, ApiError } from '../lib/api';
import { DocumentUploadModal } from './DocumentUploadModal';
import { MarkdownRenderer } from './MarkdownRenderer';
import { ArchieVoiceAssistant } from './ArchieVoiceAssistant';
import {
  Send,
  LogOut,
  RotateCcw,
  User as UserIcon,
  Bot,
  FileText,
  Clock,
  Layers,
  ShieldAlert,
  UploadCloud,
  ChevronRight,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  category?: 'policy' | 'employee' | 'hybrid' | 'out_of_scope' | 'transactional' | 'conversational';
  citations?: ChatCitation[];
  mcpToolsUsed?: string[];
  executionTimeMs?: number;
  timestamp: string;
  confirmationPrompt?: ConfirmationPrompt | null;
  transactionResult?: any;
  confirmedOrCancelled?: 'confirmed' | 'cancelled';
}

export const ChatInterface: React.FC = () => {
  const { user, token, logout } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const conversationIdRef = useRef<string>(`session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);

  // Auto-scroll to bottom of conversation
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || isLoading || !token) return;

    setErrorBanner(null);
    setInput('');

    // Append user message to thread
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);

    // Strict Security Boundary (ESR-STD-v2.4 §12.1):
    // Voice recognition and conversational statements can NEVER execute a transaction without the human confirmation button.
    const lower = query.toLowerCase().trim();
    if (
      lower === 'yes submit it' ||
      lower === 'yes, submit it.' ||
      lower === 'yes, submit it' ||
      lower === 'confirm submission' ||
      lower === 'yes confirm' ||
      lower === 'please confirm' ||
      lower === 'confirm it'
    ) {
      const refusalMsg = "For your security and corporate compliance, enterprise actions require explicit confirmation using the 'Confirm Submission' button on your screen.";
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: refusalMsg,
        category: 'transactional',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      return;
    }

    setIsLoading(true);

    try {
      const response = await api.sendChatMessage(query, token, conversationIdRef.current);

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: response.answer,
        category: response.category,
        citations: response.citations || [],
        mcpToolsUsed: response.mcp_tools_used || [],
        executionTimeMs: response.execution_time_ms,
        confirmationPrompt: response.confirmation_prompt,
        transactionResult: response.transaction_result,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 401) {
        setErrorBanner('Your session has expired. Please sign in again.');
        logout();
      } else {
        const errorMsg =
          err?.message || 'An error occurred communicating with the assistant.';
        setErrorBanner(errorMsg);

        // Append a polite system notification
        setMessages((prev) => [
          ...prev,
          {
            id: `assistant-error-${Date.now()}`,
            sender: 'assistant',
            text: `⚠️ I encountered an error while processing your request: ${errorMsg}`,
            category: 'out_of_scope',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleVoiceSubmit = async (query: string): Promise<string | void> => {
    if (!query || !token || isLoading) return;

    // Strict Security Boundary (ESR-STD-v2.4 §12.1):
    // Voice recognition and spoken requests can NEVER bypass human confirmation for transactions.
    const lower = query.toLowerCase().trim();
    if (
      lower === 'yes submit it' ||
      lower === 'yes, submit it.' ||
      lower === 'yes, submit it' ||
      lower === 'confirm submission' ||
      lower === 'yes confirm' ||
      lower === 'please confirm' ||
      lower === 'confirm it'
    ) {
      const refusalMsg = "For your security and corporate compliance, enterprise actions require explicit confirmation using the 'Confirm Submission' button on your screen.";
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        sender: 'user',
        text: query,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: refusalMsg,
        category: 'transactional',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      return refusalMsg;
    }

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await api.sendChatMessage(query, token, conversationIdRef.current);

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: response.answer,
        category: response.category,
        citations: response.citations || [],
        mcpToolsUsed: response.mcp_tools_used || [],
        executionTimeMs: response.execution_time_ms,
        confirmationPrompt: response.confirmation_prompt,
        transactionResult: response.transaction_result,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // If transactional confirmation is prepared, speak natural guidance directing user to screen
      if (response.confirmation_prompt) {
        const title = response.confirmation_prompt.summary_title || 'request';
        return `I've prepared your ${title}. Please review the dates and details on your screen and confirm when you're ready.`;
      }

      return response.answer;
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 401) {
        setErrorBanner('Your session has expired. Please sign in again.');
        logout();
      } else {
        const errorMsg =
          err?.message || 'An error occurred communicating with the assistant.';
        setErrorBanner(errorMsg);

        setMessages((prev) => [
          ...prev,
          {
            id: `assistant-error-${Date.now()}`,
            sender: 'assistant',
            text: `⚠️ I encountered an error while processing your request: ${errorMsg}`,
            category: 'out_of_scope',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
        return `I encountered an issue: ${errorMsg}`;
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmTransaction = async (msgId: string, tokenVal: string) => {
    if (!token || isLoading) return;

    // Mark current message card as confirmed
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, confirmedOrCancelled: 'confirmed' } : m))
    );

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: 'Yes, submit it.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await api.sendChatMessage(
        'Yes, submit it.',
        token,
        conversationIdRef.current,
        'confirm',
        tokenVal
      );

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: response.answer,
        category: response.category,
        citations: response.citations || [],
        mcpToolsUsed: response.mcp_tools_used || [],
        executionTimeMs: response.execution_time_ms,
        confirmationPrompt: response.confirmation_prompt,
        transactionResult: response.transaction_result,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setErrorBanner(err?.message || 'Transaction submission failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelTransaction = async (msgId: string, tokenVal: string) => {
    if (!token || isLoading) return;

    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, confirmedOrCancelled: 'cancelled' } : m))
    );

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: 'Cancel this request.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await api.sendChatMessage(
        'Cancel this request.',
        token,
        conversationIdRef.current,
        'cancel',
        tokenVal
      );

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: response.answer,
        category: response.category,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setErrorBanner(err?.message || 'Cancellation failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearConversation = () => {
    setMessages([]);
    setErrorBanner(null);
    conversationIdRef.current = `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  };

  const employeePrompts = [
    'I want to take leave from December 10 to December 12',
    'My laptop screen is broken, please raise an IT ticket',
    'I purchased an ergonomic chair for $250. Can I claim reimbursement?',
    'What is the status of my open requests and tickets?',
    'What is the annual leave carryover policy?',
    'How much annual leave do I have remaining?',
  ];

  const adminPrompts = [
    'What is the company sick leave policy?',
    "How much annual leave does Bob Jones (E102) have remaining?",
    'What laptop model is assigned to Bob Jones (E102)?',
    'What is the laptop replacement policy?',
  ];

  const promptSuggestions = user?.role === 'hr_admin' ? adminPrompts : employeePrompts;

  return (
    <div className="flex flex-col h-screen w-full max-w-6xl mx-auto bg-slate-50 border-x border-slate-200 shadow-xl overflow-hidden">
      {/* 1. Header Navigation Bar */}
      <header className="flex-shrink-0 bg-white border-b border-slate-200 px-6 py-3.5 flex items-center justify-between shadow-sm z-10">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-700 to-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
            A
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-sm font-bold text-slate-900 tracking-tight">Acme Corporation</h1>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                FY 2026
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-medium">Enterprise HR &amp; IT Assistant</p>
          </div>
        </div>

        {/* User Identity & Navigation Actions */}
        <div className="flex items-center space-x-3">
          <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200">
            <UserIcon className="w-4 h-4 text-slate-500" />
            <div className="text-left text-xs">
              <span className="font-semibold text-slate-800">
                {user?.first_name} {user?.last_name}
              </span>
              <span className="text-slate-500 ml-1">({user?.employee_number})</span>
            </div>
            <span
              className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                user?.role === 'hr_admin'
                  ? 'bg-purple-100 text-purple-800 border border-purple-200'
                  : 'bg-blue-100 text-blue-800 border border-blue-200'
              }`}
            >
              {user?.role === 'hr_admin' ? 'HR Admin' : 'Employee'}
            </span>
          </div>

          {user?.role === 'hr_admin' && (
            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-xl transition-colors"
              title="Upload policy document"
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Ingest Document</span>
            </button>
          )}

          <button
            onClick={handleClearConversation}
            className="flex items-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-colors"
            title="Reset conversation state"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Clear</span>
          </button>

          <button
            onClick={logout}
            className="flex items-center space-x-1 px-3 py-1.5 text-xs font-medium text-rose-600 hover:text-rose-700 hover:bg-rose-50 border border-rose-200 rounded-xl transition-colors"
            title="Sign out of Acme Assistant"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </header>

      {/* 1.5 Archie Personalized Voice Assistant Bar */}
      <ArchieVoiceAssistant
        user={user}
        onSubmitUtterance={handleVoiceSubmit}
        isProcessingQuery={isLoading}
      />

      {/* 2. Error Notification Banner */}
      {errorBanner && (
        <div className="bg-rose-50 border-b border-rose-200 text-rose-800 px-6 py-2.5 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{errorBanner}</span>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            className="text-rose-500 hover:text-rose-800 font-bold ml-4"
          >
            ×
          </button>
        </div>
      )}

      {/* 3. Conversation Thread */}
      <main className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 max-w-2xl mx-auto space-y-6">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Bot className="w-9 h-9" />
            </div>

            <div>
              <h2 className="text-xl font-bold text-slate-900">
                Welcome back, {user?.first_name}!
              </h2>
              <p className="text-xs text-slate-500 mt-1.5 max-w-md">
                I can help answer questions regarding company policies, retrieve your employee leave balances, view your assigned IT hardware, and inspect open support tickets.
              </p>
            </div>

            {/* Prompt Starter Chips */}
            <div className="w-full space-y-2">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider text-left">
                Suggested Questions ({user?.role === 'hr_admin' ? 'HR Admin Queries' : 'Employee Self-Service'})
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                {promptSuggestions.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(prompt)}
                    className="p-3 rounded-xl border border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50/50 text-xs text-slate-700 transition-all flex items-center justify-between group text-left shadow-sm"
                  >
                    <span className="line-clamp-2">{prompt}</span>
                    <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 flex-shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start space-x-3 ${
                msg.sender === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {msg.sender === 'assistant' && (
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center shadow flex-shrink-0 mt-0.5">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-2xl rounded-2xl px-5 py-3.5 shadow-sm ${
                  msg.sender === 'user'
                    ? 'bg-blue-600 text-white rounded-tr-none'
                    : 'bg-white border border-slate-200/80 rounded-tl-none'
                }`}
              >
                {/* Assistant Metadata Header */}
                {msg.sender === 'assistant' && (
                  <div className="flex items-center justify-end pb-1.5 mb-2 border-b border-slate-100">
                    <div className="flex items-center space-x-2 text-[10px] text-slate-400">
                      {msg.executionTimeMs && (
                        <span className="flex items-center space-x-0.5">
                          <Clock className="w-3 h-3" />
                          <span>{msg.executionTimeMs} ms</span>
                        </span>
                      )}
                      <span>{msg.timestamp}</span>
                    </div>
                  </div>
                )}

                {/* Message Body */}
                <div className="text-sm">
                  {msg.sender === 'user' ? (
                    <p className="whitespace-pre-wrap">{msg.text}</p>
                  ) : (
                    <MarkdownRenderer content={msg.text} />
                  )}
                </div>

                {/* Interactive Transaction Confirmation Card */}
                {msg.sender === 'assistant' && msg.confirmationPrompt && (
                  <div className="mt-3.5 p-3.5 bg-gradient-to-br from-blue-50/90 to-indigo-50/70 border border-blue-200/90 rounded-xl text-slate-800 shadow-xs">
                    <div className="flex items-center gap-1.5 font-semibold text-blue-900 text-xs mb-2">
                      <ShieldAlert className="w-4 h-4 text-blue-600" />
                      <span>{msg.confirmationPrompt.summary_title || 'Confirmation Required'}</span>
                    </div>

                    <div className="bg-white/95 border border-blue-100 rounded-lg p-2.5 my-2 divide-y divide-slate-100 text-xs">
                      {Object.entries(msg.confirmationPrompt.details || {}).map(([key, val]) => (
                        <div key={key} className="py-1.5 flex justify-between gap-4 text-xs">
                          <span className="font-medium text-slate-500">{key}:</span>
                          <span className="font-semibold text-slate-800 text-right">{String(val)}</span>
                        </div>
                      ))}
                    </div>

                    {msg.confirmedOrCancelled ? (
                      <div className={`mt-2.5 text-xs font-semibold px-2.5 py-1 rounded inline-flex items-center gap-1 ${
                        msg.confirmedOrCancelled === 'confirmed'
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                          : 'bg-slate-200 text-slate-700 border border-slate-300'
                      }`}>
                        {msg.confirmedOrCancelled === 'confirmed' ? (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                            <span>Action Confirmed & Executed</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-3.5 h-3.5 text-slate-500" />
                            <span>Action Cancelled</span>
                          </>
                        )}
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 mt-3 pt-2.5 border-t border-blue-100/80">
                        <button
                          onClick={() => handleConfirmTransaction(msg.id, msg.confirmationPrompt!.confirmation_token)}
                          disabled={isLoading}
                          className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Confirm Submission</span>
                        </button>
                        <button
                          onClick={() => handleCancelTransaction(msg.id, msg.confirmationPrompt!.confirmation_token)}
                          disabled={isLoading}
                          className="px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* Structured Policy Citations (Rendered ONLY when genuine citations exist) */}
                {msg.sender === 'assistant' && msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3.5 pt-3 border-t border-slate-100 space-y-1.5">
                    <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center">
                      <FileText className="w-3.5 h-3.5 mr-1 text-slate-400" />
                      Authoritative Policy Citations ({msg.citations.length})
                    </p>
                    <div className="grid grid-cols-1 gap-1.5">
                      {msg.citations.map((cite, cIdx) => (
                        <div
                          key={cIdx}
                          className="bg-slate-50 rounded-lg p-2.5 border border-slate-200 text-xs space-y-0.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-slate-800">
                              {cite.document_title}
                            </span>
                            <span className="text-[10px] font-mono text-slate-500 bg-white px-1.5 py-0.5 rounded border border-slate-200">
                              {cite.filename}
                            </span>
                          </div>
                          <div className="flex items-center space-x-2 text-[11px] text-slate-600">
                            <span>
                              Section: <strong>{cite.section}</strong>
                            </span>
                            {cite.page_number && (
                              <>
                                <span>•</span>
                                <span>
                                  Page: <strong>{cite.page_number}</strong>
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* MCP Tools Used Badges */}
                {msg.sender === 'assistant' && msg.mcpToolsUsed && msg.mcpToolsUsed.length > 0 && (
                  <div className="mt-2.5 flex items-center space-x-1.5 text-[10px] text-slate-500">
                    <Layers className="w-3 h-3 text-slate-400" />
                    <span className="font-medium">MCP Tools:</span>
                    {msg.mcpToolsUsed.map((tool, tIdx) => (
                      <span
                        key={tIdx}
                        className="bg-slate-100 text-slate-700 font-mono px-1.5 py-0.5 rounded text-[10px]"
                      >
                        {tool}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {msg.sender === 'user' && (
                <div className="w-8 h-8 rounded-xl bg-slate-800 text-white flex items-center justify-center shadow flex-shrink-0 mt-0.5 text-xs font-bold">
                  {user?.first_name?.charAt(0) || 'U'}
                </div>
              )}
            </div>
          ))
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center shadow flex-shrink-0 mt-0.5">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm flex items-center space-x-2">
              <div className="w-2 h-2 rounded-full bg-blue-600 animate-bounce [animation-delay:-0.3s]"></div>
              <div className="w-2 h-2 rounded-full bg-blue-600 animate-bounce [animation-delay:-0.15s]"></div>
              <div className="w-2 h-2 rounded-full bg-blue-600 animate-bounce"></div>
              <span className="text-xs text-slate-500 font-medium ml-2">
                Consulting policy documents &amp; employee records...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </main>

      {/* 4. Input Bar */}
      <footer className="flex-shrink-0 bg-white border-t border-slate-200 p-4">
        <div className="relative flex items-center">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask a company policy or ${user?.role === 'hr_admin' ? 'employee' : 'personal'} question... (Enter to send)`}
            disabled={isLoading}
            className="w-full resize-none rounded-xl border border-slate-300 py-3 pl-4 pr-14 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all placeholder:text-slate-400 disabled:opacity-50"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            className="absolute right-2 p-2 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-40 text-white transition-colors"
            title="Send query"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[10px] text-slate-400 text-center mt-2">
          Responses derive strictly from ingested enterprise policy documents and authorized employee database records.
        </p>
      </footer>

      {/* HR Admin Ingestion Modal */}
      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
      />
    </div>
  );
};
