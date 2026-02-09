import { useState, useRef } from 'react';
import { X, Loader2, Download, Save, Check, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import { generateResume, saveResume } from '../services/jobs';

interface ResumeModalProps {
  jobId: number;
  jobTitle: string;
  company?: string;
  onClose: () => void;
}

export default function ResumeModal({ jobId, jobTitle, company, onClose }: ResumeModalProps) {
  const [language, setLanguage] = useState<'english' | 'german'>('english');
  const [instructions, setInstructions] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [resumeHtml, setResumeHtml] = useState<string | null>(null);
  const [savedResumeId, setSavedResumeId] = useState<number | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [error, setError] = useState('');
  const contentRef = useRef<HTMLDivElement>(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError('');
    try {
      const result = await generateResume(jobId, { language, instructions: instructions.trim() || undefined });
      if (result.success && result.resume_html) {
        setResumeHtml(result.resume_html);
      } else {
        setError(result.error || 'Failed to generate resume');
      }
    } catch (err) {
      setError((err as Error).message || 'Failed to generate resume');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!resumeHtml) return;
    setIsSaving(true);
    setError('');
    try {
      // Get potentially edited HTML from contentEditable div
      const editedHtml = contentRef.current?.innerHTML || resumeHtml;
      const result = await saveResume(jobId, editedHtml);
      if (result.success) {
        setSavedResumeId(result.resume_id || null);
        setPdfUrl(result.pdf_url || null);
      } else {
        setError(result.error || 'Failed to save resume');
      }
    } catch (err) {
      setError((err as Error).message || 'Failed to save resume');
    } finally {
      setIsSaving(false);
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
              <h2 className="text-lg font-semibold text-slate-900">Generate Resume</h2>
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
          {!resumeHtml ? (
            /* State A: Options */
            <div className="max-w-xl mx-auto py-12 px-6 space-y-8">
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

              {/* Instructions */}
              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-2">
                  Additional Instructions <span className="font-normal text-slate-400">(optional)</span>
                </label>
                <textarea
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="e.g. Emphasize leadership experience, keep it to one page..."
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
                    Generating resume...
                  </>
                ) : (
                  'Generate Resume'
                )}
              </button>
            </div>
          ) : (
            /* State B: Result */
            <div className="flex flex-col h-full">
              {/* Action bar */}
              <div className="flex items-center gap-3 px-6 py-3 bg-slate-50 border-b border-slate-200 flex-shrink-0">
                {savedResumeId ? (
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
                    Save Resume
                  </button>
                )}

                {pdfUrl && (
                  <a
                    href={pdfUrl}
                    className="px-5 py-2 border border-cyan-200 text-cyan-600 text-sm font-semibold rounded-xl hover:bg-cyan-50 transition-colors flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    Download PDF
                  </a>
                )}

                {savedResumeId && (
                  <a
                    href={`/download/resume/${savedResumeId}?format=html`}
                    className="px-5 py-2 border border-slate-200 text-slate-600 text-sm font-medium rounded-xl hover:bg-slate-50 transition-colors flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    Download HTML
                  </a>
                )}

                {error && (
                  <span className="text-sm text-rose-600 ml-auto">{error}</span>
                )}
              </div>

              {/* Editable resume preview */}
              <div className="flex-1 overflow-y-auto p-6">
                <p className="text-xs text-slate-400 mb-3 italic">Click on the resume below to edit directly</p>
                <div
                  ref={contentRef}
                  contentEditable
                  suppressContentEditableWarning
                  className="mx-auto max-w-[800px] bg-white border border-slate-200 rounded-xl shadow-sm p-8 focus:outline-none focus:ring-2 focus:ring-cyan-300"
                  dangerouslySetInnerHTML={{ __html: resumeHtml }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
