'use client';

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, LogIn, AlertCircle, Loader2, UserCheck } from 'lucide-react';

export const LoginForm: React.FC = () => {
  const { login, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState('bob@acme.com');
  const [password, setPassword] = useState('Password123!');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim() || !password) {
      setLocalError('Please enter both corporate email and password.');
      return;
    }

    try {
      await login(email, password);
    } catch (err: any) {
      // Error is set in context
    }
  };

  const setDemoAccount = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword('Password123!');
    setLocalError(null);
    clearError();
  };

  const displayError = localError || error;

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-white rounded-2xl shadow-xl border border-slate-200/80 overflow-hidden">
        {/* Header Banner */}
        <div className="bg-gradient-to-r from-blue-700 to-indigo-800 p-8 text-white text-center relative">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white/10 backdrop-blur-md mb-4 border border-white/20 shadow-inner">
            <ShieldCheck className="w-8 h-8 text-blue-200" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Acme Assistant</h1>
          <p className="text-blue-100 text-xs mt-1 font-medium">
            Universal Enterprise HR &amp; IT Helpdesk
          </p>
        </div>

        {/* Form Body */}
        <div className="p-8 space-y-6">
          {displayError && (
            <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-xl p-4 text-xs flex items-start space-x-3 animate-fadeIn">
              <AlertCircle className="w-4 h-4 text-rose-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-semibold">Authentication Failed</p>
                <p className="mt-0.5 text-rose-700">{displayError}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5"
              >
                Corporate Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@acme.com"
                required
                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all placeholder:text-slate-400"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all placeholder:text-slate-400"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 rounded-xl font-medium text-sm text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-60 transition-colors shadow-md shadow-blue-500/20 flex items-center justify-center space-x-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  <span>Sign In</span>
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Credentials */}
          <div className="pt-4 border-t border-slate-100">
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider text-center mb-3">
              One-Click Demo Logins (Acme Baseline)
            </p>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setDemoAccount('bob@acme.com')}
                className="p-2.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-blue-50 hover:border-blue-200 text-left transition-colors group"
              >
                <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-800 group-hover:text-blue-700">
                  <UserCheck className="w-3.5 h-3.5 text-blue-600" />
                  <span>Bob Jones</span>
                </div>
                <p className="text-[10px] text-slate-500 mt-0.5">
                  E102 • Employee
                </p>
              </button>

              <button
                type="button"
                onClick={() => setDemoAccount('alice@acme.com')}
                className="p-2.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-indigo-50 hover:border-indigo-200 text-left transition-colors group"
              >
                <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-800 group-hover:text-indigo-700">
                  <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Alice Smith</span>
                </div>
                <p className="text-[10px] text-slate-500 mt-0.5">
                  E101 • HR Admin
                </p>
              </button>
            </div>

            <button
              type="button"
              onClick={() => setDemoAccount('david@acme.com')}
              className="mt-2 w-full p-1.5 text-[11px] text-slate-400 hover:text-slate-600 text-center block transition-colors"
            >
              Test deactivated account (David Miller E104)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
