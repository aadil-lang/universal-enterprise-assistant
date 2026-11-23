'use client';

import React from 'react';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { LoginForm } from '../components/LoginForm';
import { ChatInterface } from '../components/ChatInterface';
import { Loader2 } from 'lucide-react';

function MainApp() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-screen bg-slate-50">
        <div className="flex flex-col items-center space-y-3">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
          <p className="text-xs text-slate-500 font-medium">Loading Acme Assistant...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/40 p-4">
        <LoginForm />
      </div>
    );
  }

  return <ChatInterface />;
}

export default function HomePage() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
