'use client';

import React, { useState } from 'react';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { UploadCloud, CheckCircle, AlertCircle, Loader2, X, FileText } from 'lucide-react';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({ isOpen, onClose }) => {
  const { token, user } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState<'HR' | 'IT'>('HR');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<any | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  if (!isOpen) return null;

  // Authorization safeguard
  if (user?.role !== 'hr_admin') {
    return (
      <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl border border-slate-200">
          <div className="flex items-center space-x-3 text-rose-600 mb-4">
            <AlertCircle className="w-6 h-6" />
            <h3 className="font-bold text-base">Access Denied</h3>
          </div>
          <p className="text-sm text-slate-600 mb-6">
            Document ingestion requires HR Administrator permissions.
          </p>
          <button
            onClick={onClose}
            className="w-full py-2 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      const ext = selected.name.split('.').pop()?.toLowerCase();
      if (!['pdf', 'docx', 'md'].includes(ext || '')) {
        setUploadError('Unsupported format. Only PDF, DOCX, and Markdown (.md) documents are accepted.');
        setFile(null);
        return;
      }
      setUploadError(null);
      setFile(selected);
      if (!title) {
        // Auto-fill title from filename
        setTitle(selected.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' '));
      }
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !token) {
      setUploadError('Please select a valid document file.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadResult(null);

    try {
      const result = await api.uploadDocument(file, title, category, token);
      setUploadResult(result);
      setFile(null);
      setTitle('');
    } catch (err: any) {
      const msg = err?.message || 'Failed to ingest document.';
      setUploadError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden animate-fadeIn">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Ingest Policy Document</h2>
              <p className="text-[11px] text-slate-500">
                HR Admin Knowledge Base Ingestion Pipeline
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">
          {uploadError && (
            <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-xl p-3.5 text-xs flex items-start space-x-2.5">
              <AlertCircle className="w-4 h-4 text-rose-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-semibold">Ingestion Rejected</p>
                <p className="text-rose-700 mt-0.5">{uploadError}</p>
              </div>
            </div>
          )}

          {uploadResult && (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-xl p-4 text-xs space-y-1.5">
              <div className="flex items-center space-x-2 text-emerald-700 font-semibold">
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                <span>Document Ingested &amp; Indexed Successfully!</span>
              </div>
              <p className="text-emerald-800">
                Title: <strong>{uploadResult.title}</strong>
              </p>
              <p className="text-emerald-800">
                Chunks Generated: <strong>{uploadResult.chunk_count}</strong> | Status: <strong>{uploadResult.status}</strong>
              </p>
            </div>
          )}

          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Document File (.pdf, .docx, .md)
              </label>
              <div className="border-2 border-dashed border-slate-200 rounded-xl p-4 text-center hover:border-indigo-400 transition-colors bg-slate-50/50">
                <input
                  type="file"
                  id="doc-file-input"
                  accept=".pdf,.docx,.md"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <label
                  htmlFor="doc-file-input"
                  className="cursor-pointer flex flex-col items-center justify-center space-y-2"
                >
                  <FileText className="w-8 h-8 text-indigo-500" />
                  <span className="text-xs font-medium text-slate-700">
                    {file ? file.name : 'Click to select policy file'}
                  </span>
                  <span className="text-[10px] text-slate-400">
                    Supported: PDF, DOCX, Markdown (.md)
                  </span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Document Title (Optional)
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Acme Remote Work Policy 2026"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-slate-900 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as 'HR' | 'IT')}
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-slate-900 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="HR">Human Resources (HR)</option>
                <option value="IT">Information Technology (IT)</option>
              </select>
            </div>

            <div className="pt-2 flex items-center justify-end space-x-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-100 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!file || isUploading}
                className="px-4 py-2 rounded-xl text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center space-x-1.5"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Indexing...</span>
                  </>
                ) : (
                  <>
                    <UploadCloud className="w-3.5 h-3.5" />
                    <span>Upload &amp; Index</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
