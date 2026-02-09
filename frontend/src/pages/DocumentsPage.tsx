import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  FileText,
  Download,
  Trash2,
  Building2,
  Loader2,
  AlertCircle,
  FolderOpen,
} from 'lucide-react';
import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';
import { getDocuments, deleteResume, deleteCoverLetter } from '../services/jobs';
import type { DocumentCard } from '../types';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentCard[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadDocuments = async () => {
    try {
      const data = await getDocuments();
      setDocuments(data.documents);
    } catch (err) {
      setError((err as Error).message || 'Failed to load documents');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleDeleteResume = async (resumeId: number) => {
    const key = `resume-${resumeId}`;
    setDeletingId(key);
    try {
      await deleteResume(resumeId);
      setDocuments((prev) =>
        prev
          .map((doc) =>
            doc.resume?.id === resumeId ? { ...doc, resume: undefined } : doc
          )
          .filter((doc) => doc.resume || doc.cover_letter)
      );
    } catch (err) {
      console.error('Failed to delete resume:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteCoverLetter = async (clId: number) => {
    const key = `cl-${clId}`;
    setDeletingId(key);
    try {
      await deleteCoverLetter(clId);
      setDocuments((prev) =>
        prev
          .map((doc) =>
            doc.cover_letter?.id === clId ? { ...doc, cover_letter: undefined } : doc
          )
          .filter((doc) => doc.resume || doc.cover_letter)
      );
    } catch (err) {
      console.error('Failed to delete cover letter:', err);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-cyan-50/30">
      <Header />

      <main className="pt-28 pb-16 px-6">
        <div className="max-w-4xl mx-auto">
          {/* Page header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="border border-cyan-200 rounded-2xl p-8 bg-white shadow-sm mb-8"
          >
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <FileText className="w-6 h-6 text-cyan-600" strokeWidth={1.5} />
              My Documents
            </h1>
            <p className="text-slate-500 text-sm mt-1">
              {isLoading
                ? 'Loading...'
                : `${documents.length} job${documents.length !== 1 ? 's' : ''} with saved documents`}
            </p>
          </motion.div>

          {/* Loading */}
          {isLoading && (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-cyan-600 animate-spin" />
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="text-center py-16">
              <AlertCircle className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">{error}</p>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && documents.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-20"
            >
              <FolderOpen className="w-12 h-12 text-slate-300 mx-auto mb-4" strokeWidth={1.5} />
              <h3 className="text-lg font-semibold text-slate-700 mb-2">No documents yet</h3>
              <p className="text-slate-500 text-sm max-w-md mx-auto">
                Generate a resume or cover letter from a job detail page to get started.
              </p>
            </motion.div>
          )}

          {/* Document cards */}
          {!isLoading && documents.length > 0 && (
            <div className="space-y-4">
              {documents.map((doc) => (
                <motion.div
                  key={doc.job_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="border border-cyan-200 rounded-2xl bg-white shadow-sm p-6"
                >
                  {/* Job header */}
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-base font-semibold text-slate-900">{doc.job_title}</h3>
                      {doc.job_company && (
                        <span className="flex items-center gap-1 text-sm text-slate-500 mt-1">
                          <Building2 className="w-3.5 h-3.5" />
                          {doc.job_company}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-slate-400">
                      {doc.latest_date ? new Date(doc.latest_date).toLocaleDateString() : ''}
                    </span>
                  </div>

                  <div className="space-y-3">
                    {/* Resume row */}
                    {doc.resume && (
                      <div className="flex items-center justify-between bg-slate-50 rounded-xl px-4 py-3">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-cyan-600" />
                          <span className="text-sm font-medium text-slate-700">Resume</span>
                          <span className="text-xs text-slate-400">
                            {doc.resume.created_at ? new Date(doc.resume.created_at).toLocaleDateString() : ''}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <a
                            href={`/download/resume/${doc.resume.id}?format=html`}
                            className="px-3 py-1.5 text-xs font-medium text-cyan-600 border border-cyan-200 rounded-lg hover:bg-cyan-50 transition-colors flex items-center gap-1"
                          >
                            <Download className="w-3 h-3" />
                            HTML
                          </a>
                          {doc.resume.pdf_exists && (
                            <a
                              href={`/download/resume/${doc.resume.id}?format=pdf`}
                              className="px-3 py-1.5 text-xs font-medium text-cyan-600 border border-cyan-200 rounded-lg hover:bg-cyan-50 transition-colors flex items-center gap-1"
                            >
                              <Download className="w-3 h-3" />
                              PDF
                            </a>
                          )}
                          <button
                            onClick={() => handleDeleteResume(doc.resume!.id)}
                            disabled={deletingId === `resume-${doc.resume.id}`}
                            className="p-1.5 text-slate-400 hover:text-rose-500 transition-colors rounded-lg hover:bg-rose-50 disabled:opacity-50"
                          >
                            {deletingId === `resume-${doc.resume.id}` ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Trash2 className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Cover letter row */}
                    {doc.cover_letter && (
                      <div className="flex items-center justify-between bg-slate-50 rounded-xl px-4 py-3">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-indigo-600" />
                          <span className="text-sm font-medium text-slate-700">Cover Letter</span>
                          <span className="text-xs text-slate-400">
                            {doc.cover_letter.created_at ? new Date(doc.cover_letter.created_at).toLocaleDateString() : ''}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {doc.cover_letter.pdf_exists && (
                            <a
                              href={`/download/cover-letter/${doc.cover_letter.id}?format=pdf`}
                              className="px-3 py-1.5 text-xs font-medium text-cyan-600 border border-cyan-200 rounded-lg hover:bg-cyan-50 transition-colors flex items-center gap-1"
                            >
                              <Download className="w-3 h-3" />
                              PDF
                            </a>
                          )}
                          <a
                            href={`/download/cover-letter/${doc.cover_letter.id}?format=txt`}
                            className="px-3 py-1.5 text-xs font-medium text-cyan-600 border border-cyan-200 rounded-lg hover:bg-cyan-50 transition-colors flex items-center gap-1"
                          >
                            <Download className="w-3 h-3" />
                            TXT
                          </a>
                          <button
                            onClick={() => handleDeleteCoverLetter(doc.cover_letter!.id)}
                            disabled={deletingId === `cl-${doc.cover_letter.id}`}
                            className="p-1.5 text-slate-400 hover:text-rose-500 transition-colors rounded-lg hover:bg-rose-50 disabled:opacity-50"
                          >
                            {deletingId === `cl-${doc.cover_letter.id}` ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Trash2 className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
