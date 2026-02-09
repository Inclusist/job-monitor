import { useState } from 'react';
import { X, Loader2, Save, Check, Copy, Download, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import { generateCoverLetter, saveCoverLetter } from '../services/jobs';
import type { CoverLetterStyle } from '../types';

const COVER_LETTER_STYLES: CoverLetterStyle[] = [
  { key: 'professional', name: 'Professional & Formal', description: 'Traditional business tone', best_for: 'Corporate, finance, consulting' },
  { key: 'technical', name: 'Technical & Detailed', description: 'Emphasizes technical skills', best_for: 'Engineering, data science, DevOps' },
  { key: 'results', name: 'Results-Oriented', description: 'Focus on achievements', best_for: 'Sales, marketing, growth roles' },
  { key: 'conversational', name: 'Modern & Conversational', description: 'Friendly yet professional', best_for: 'Startups, tech companies' },
  { key: 'enthusiastic', name: 'Enthusiastic & Passionate', description: 'Shows excitement and cultural fit', best_for: 'Mission-driven companies' },
  { key: 'executive', name: 'Executive & Strategic', description: 'High-level leadership perspective', best_for: 'Senior/C-suite positions' },
];

interface CoverLetterModalProps {
  jobId: number;
  jobTitle: string;
  company?: string;
  onClose: () => void;
}

export default function CoverLetterModal({ jobId, jobTitle, company, onClose }: CoverLetterModalProps) {
  const [language, setLanguage] = useState<'english' | 'german'>('english');
  const [style, setStyle] = useState('professional');
  const [instructions, setInstructions] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [coverLetterText, setCoverLetterText] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError('');
    try {
      const result = await generateCoverLetter(jobId, {
        language,
        style,
        instructions: instructions.trim() || undefined,
      });
      if (result.success && result.cover_letter_text) {
        setCoverLetterText(result.cover_letter_text);
      } else {
        setError(result.error || 'Failed to generate cover letter');
      }
    } catch (err) {
      setError((err as Error).message || 'Failed to generate cover letter');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!coverLetterText) return;
    setIsSaving(true);
    setError('');
    try {
      const result = await saveCoverLetter(jobId, coverLetterText);
      if (result.success) {
        setSavedId(result.cover_letter_id || null);
      } else {
        setError(result.error || 'Failed to save cover letter');
      }
    } catch (err) {
      setError((err as Error).message || 'Failed to save cover letter');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopy = async () => {
    if (!coverLetterText) return;
    try {
      await navigator.clipboard.writeText(coverLetterText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white w-full h-full flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-cyan-200 flex-shrink-0">
          <div className="flex items-center gap-4">
            <Link
              to="/jobs"
              className="flex items-center gap-1 text-sm text-slate-500 hover:text-cyan-600 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Jobs
            </Link>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Generate Cover Letter</h2>
              <p className="text-sm text-slate-500">{jobTitle}{company ? ` — ${company}` : ''}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {!coverLetterText ? (
            /* State A: Options */
            <div className="max-w-2xl mx-auto py-12 px-6 space-y-8">
              {/* Language toggle */}
              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-3">Language</label>
                <div className="flex gap-3">
                  {(['english', 'german'] as const).map((lang) => (
                    <button
                      key={lang}
                      onClick={() => setLanguage(lang)}
                      className={`px-5 py-2.5 rounded-xl text-sm font-medium border transition-colors ${
                        language === lang
                          ? 'bg-cyan-600 text-white border-cyan-600'
                          : 'bg-white text-slate-600 border-slate-200 hover:border-cyan-300'
                      }`}
                    >
                      {lang === 'english' ? 'English' : 'German'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Style selector */}
              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-3">Style</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {COVER_LETTER_STYLES.map((s) => (
                    <button
                      key={s.key}
                      onClick={() => setStyle(s.key)}
                      className={`text-left p-4 rounded-xl border transition-colors ${
                        style === s.key
                          ? 'border-cyan-500 bg-cyan-50 ring-2 ring-cyan-200'
                          : 'border-slate-200 bg-white hover:border-cyan-300'
                      }`}
                    >
                      <div className="text-sm font-semibold text-slate-900">{s.name}</div>
                      <div className="text-xs text-slate-500 mt-1">{s.description}</div>
                      <div className="text-xs text-slate-400 mt-1">Best for: {s.best_for}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Instructions */}
              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-2">
                  Additional Instructions <span className="font-normal text-slate-400">(optional)</span>
                </label>
                <textarea
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="e.g. Mention my passion for sustainability, keep it concise..."
                  rows={4}
                  className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent resize-none"
                />
              </div>

              {error && (
                <div className="text-sm text-rose-600 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3">
                  {error}
                </div>
              )}

              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="w-full px-6 py-3 bg-cyan-600 text-white text-sm font-semibold rounded-xl hover:bg-cyan-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating cover letter...
                  </>
                ) : (
                  'Generate Cover Letter'
                )}
              </button>
            </div>
          ) : (
            /* State B: Result */
            <div className="flex flex-col h-full">
              {/* Action bar */}
              <div className="flex items-center gap-3 px-6 py-3 bg-slate-50 border-b border-slate-200 flex-shrink-0">
                {savedId ? (
                  <span className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-600">
                    <Check className="w-4 h-4" />
                    Saved successfully
                  </span>
                ) : (
                  <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="px-5 py-2 bg-cyan-600 text-white text-sm font-semibold rounded-xl hover:bg-cyan-500 transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save Cover Letter
                  </button>
                )}

                <button
                  onClick={handleCopy}
                  className="px-5 py-2 border border-slate-200 text-slate-600 text-sm font-medium rounded-xl hover:bg-slate-50 transition-colors flex items-center gap-2"
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>

                {savedId && (
                  <>
                    <a
                      href={`/download/cover-letter/${savedId}?format=pdf`}
                      className="px-5 py-2 border border-cyan-200 text-cyan-600 text-sm font-semibold rounded-xl hover:bg-cyan-50 transition-colors flex items-center gap-2"
                    >
                      <Download className="w-4 h-4" />
                      Download PDF
                    </a>
                    <a
                      href={`/download/cover-letter/${savedId}?format=txt`}
                      className="px-5 py-2 border border-slate-200 text-slate-600 text-sm font-medium rounded-xl hover:bg-slate-50 transition-colors flex items-center gap-2"
                    >
                      <Download className="w-4 h-4" />
                      Download TXT
                    </a>
                  </>
                )}

                {error && (
                  <span className="text-sm text-rose-600 ml-auto">{error}</span>
                )}
              </div>

              {/* Editable cover letter */}
              <div className="flex-1 overflow-y-auto p-6">
                <div className="max-w-[700px] mx-auto">
                  <p className="text-xs text-slate-400 mb-3 italic">Edit the cover letter below as needed</p>
                  <textarea
                    value={coverLetterText}
                    onChange={(e) => setCoverLetterText(e.target.value)}
                    className="w-full min-h-[500px] px-6 py-5 border border-slate-200 rounded-xl text-sm text-slate-700 leading-relaxed font-serif focus:outline-none focus:ring-2 focus:ring-cyan-300 resize-y"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
