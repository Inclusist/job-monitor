import { useState, useEffect, useRef, useCallback } from 'react';
import { X, Loader2, Save, Check, Eye, Pencil } from 'lucide-react';
import { getResumeContent, getCoverLetterContent, saveResume, saveCoverLetter } from '../../services/jobs';

type DocType = 'resume' | 'cover_letter';
type Mode = 'view' | 'edit';

interface DocumentViewerModalProps {
  docType: DocType;
  docId: number;
  initialMode: Mode;
  onClose: () => void;
  onSaved?: () => void;
}

export default function DocumentViewerModal({ docType, docId, initialMode, onClose, onSaved }: DocumentViewerModalProps) {
  const [mode, setMode] = useState<Mode>(initialMode);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [content, setContent] = useState('');
  const [editContent, setEditContent] = useState('');
  const [jobId, setJobId] = useState<number | null>(null);
  const [jobTitle, setJobTitle] = useState('');
  const [jobCompany, setJobCompany] = useState('');
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      setError('');
      try {
        if (docType === 'resume') {
          const data = await getResumeContent(docId);
          setContent(data.resume_html);
          setEditContent(data.resume_html);
          setJobId(data.job_id);
          setJobTitle(data.job_title || '');
          setJobCompany(data.job_company || '');
        } else {
          const data = await getCoverLetterContent(docId);
          setContent(data.cover_letter_text);
          setEditContent(data.cover_letter_text);
          setJobId(data.job_id);
          setJobTitle(data.job_title || '');
          setJobCompany(data.job_company || '');
        }
      } catch (err) {
        setError((err as Error).message || 'Failed to load document');
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [docType, docId]);

  const writeToIframe = useCallback((html: string) => {
    const iframe = iframeRef.current;
    if (!iframe) return;
    const doc = iframe.contentDocument;
    if (!doc) return;
    doc.open();
    doc.write(html);
    doc.close();
  }, []);

  useEffect(() => {
    if (mode === 'view' && docType === 'resume' && content && !isLoading) {
      // Small delay to ensure iframe is mounted
      const timer = setTimeout(() => writeToIframe(content), 50);
      return () => clearTimeout(timer);
    }
  }, [mode, docType, content, isLoading, writeToIframe]);

  const handleSave = async () => {
    if (jobId === null) return;
    setIsSaving(true);
    setError('');
    setSaved(false);
    try {
      if (docType === 'resume') {
        await saveResume(jobId, editContent);
      } else {
        await saveCoverLetter(jobId, editContent);
      }
      setContent(editContent);
      setSaved(true);
      onSaved?.();
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError((err as Error).message || 'Failed to save');
    } finally {
      setIsSaving(false);
    }
  };

  const switchToEdit = () => {
    setEditContent(content);
    setMode('edit');
  };

  const switchToView = () => {
    setMode('view');
  };

  const label = docType === 'resume' ? 'Resume' : 'Cover Letter';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white w-full h-full flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-cyan-200 flex-shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              {mode === 'view' ? 'View' : 'Edit'} {label}
            </h2>
            <p className="text-sm text-slate-500">
              {jobTitle}{jobCompany ? ` — ${jobCompany}` : ''}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Mode toggle */}
            {!isLoading && (
              <>
                <button
                  onClick={switchToView}
                  className={`p-2 rounded-lg transition-colors ${
                    mode === 'view'
                      ? 'bg-cyan-100 text-cyan-700'
                      : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
                  }`}
                  title="View"
                >
                  <Eye className="w-4 h-4" />
                </button>
                <button
                  onClick={switchToEdit}
                  className={`p-2 rounded-lg transition-colors ${
                    mode === 'edit'
                      ? 'bg-cyan-100 text-cyan-700'
                      : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
                  }`}
                  title="Edit"
                >
                  <Pencil className="w-4 h-4" />
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Action bar for edit mode */}
        {mode === 'edit' && !isLoading && (
          <div className="flex items-center gap-3 px-6 py-3 bg-slate-50 border-b border-slate-200 flex-shrink-0">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-5 py-2 bg-cyan-600 text-white text-sm font-semibold rounded-xl hover:bg-cyan-500 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isSaving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : saved ? (
                <Check className="w-4 h-4" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              {saved ? 'Saved' : 'Save'}
            </button>
            {error && (
              <span className="text-sm text-rose-600">{error}</span>
            )}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-8 h-8 text-cyan-600 animate-spin" />
            </div>
          ) : error && !content ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-slate-500">{error}</p>
            </div>
          ) : mode === 'view' ? (
            docType === 'resume' ? (
              <iframe
                ref={iframeRef}
                title="Resume preview"
                className="w-full h-full border-0"
                sandbox="allow-same-origin"
              />
            ) : (
              <div className="max-w-3xl mx-auto px-6 py-8">
                <div className="whitespace-pre-wrap text-slate-700 text-sm leading-relaxed">
                  {content}
                </div>
              </div>
            )
          ) : (
            /* Edit mode */
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full h-full p-6 text-sm text-slate-700 font-mono resize-none focus:outline-none"
              spellCheck={false}
            />
          )}
        </div>
      </div>
    </div>
  );
}
