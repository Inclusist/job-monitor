import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MessageSquare, 
  X, 
  Star, 
  Target, 
  FileText, 
  LayoutDashboard, 
  Monitor,
  UserCheck,
  Check,
  Loader2,
  AlertCircle,
  ArrowRight,
  ChevronLeft
} from 'lucide-react';
import { submitToolFeedback } from '../../services/jobs';
import { useMutation } from '@tanstack/react-query';

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface RatingCategory {
  id: string;
  label: string;
  description: string;
  icon: any;
}

const CATEGORIES: RatingCategory[] = [
  { 
    id: 'matching', 
    label: 'AI Matching Accuracy', 
    description: 'Relevance of suggested jobs to your profile',
    icon: Target 
  },
  { 
    id: 'documents', 
    label: 'Document Quality', 
    description: 'Quality of generated resumes and cover letters',
    icon: FileText 
  },
  { 
    id: 'parsing', 
    label: 'CV Parsing', 
    description: 'Accuracy of profile data extraction from your CV',
    icon: UserCheck 
  },
  { 
    id: 'dashboard', 
    label: 'Dashboard Utility', 
    description: 'Usefulness of application tracking features',
    icon: LayoutDashboard 
  },
  { 
    id: 'ui', 
    label: 'Interface & UX', 
    description: 'Ease of use, design, and navigation',
    icon: Monitor 
  },
];

export default function FeedbackModal({ isOpen, onClose }: FeedbackModalProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [hoverRatings, setHoverRatings] = useState<Record<string, number>>({});
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const mutation = useMutation({
    mutationFn: () => submitToolFeedback({
      ratings,
      comment
    }),
    onSuccess: () => {
      setSubmitted(true);
      setTimeout(() => {
        handleClose();
      }, 2500);
    },
  });

  const handleClose = () => {
    onClose();
    setTimeout(() => {
      setStep(1);
      setRatings({});
      setComment('');
      setSubmitted(false);
      mutation.reset();
    }, 300);
  };

  const handleSetRating = (categoryId: string, value: number) => {
    setRatings(prev => ({ ...prev, [categoryId]: value }));
  };

  const handleHoverRating = (categoryId: string, value: number) => {
    setHoverRatings(prev => ({ ...prev, [categoryId]: value }));
  };

  const isStep1Valid = Object.keys(ratings).length > 0;

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-6 overflow-hidden">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
          />
          
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative w-full max-w-xl bg-white rounded-3xl shadow-2xl border border-cyan-100 flex flex-col max-h-[90vh]"
          >
            {/* Header */}
            <div className="px-8 py-6 border-b border-slate-100 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-cyan-50 text-cyan-600 rounded-xl">
                  <MessageSquare className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900 leading-tight">How are we doing?</h2>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-0.5">
                    {step === 1 ? 'Step 1: Ratings' : 'Step 2: Comments (Optional)'}
                  </p>
                </div>
              </div>
              <button 
                onClick={handleClose}
                className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content Area - Scrollable */}
            <div className="p-8 overflow-y-auto custom-scrollbar">
              {submitted ? (
                <div className="py-12 text-center">
                  <div className="w-20 h-20 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Check className="w-10 h-10" strokeWidth={3} />
                  </div>
                  <h3 className="text-2xl font-bold text-slate-900 mb-2">Thank You!</h3>
                  <p className="text-slate-600">Your feedback helps us build a better Inclusist.</p>
                </div>
              ) : step === 1 ? (
                <div className="space-y-6">
                  <p className="text-sm text-slate-600 leading-relaxed italic border-l-4 border-cyan-200 pl-4 mb-8">
                    "Please rate the core aspects of the tool. Your input directly influences our development roadmap."
                  </p>
                  
                  <div className="space-y-5">
                    {CATEGORIES.map((cat) => {
                      const Icon = cat.icon;
                      const currentRating = ratings[cat.id] || 0;
                      const currentHover = hoverRatings[cat.id] || 0;
                      
                      return (
                        <div key={cat.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl bg-slate-50 border border-slate-100 hover:bg-white hover:border-cyan-100 transition-all group">
                          <div className="flex items-center gap-3">
                            <div className="p-2.5 bg-white text-cyan-600 rounded-xl shadow-sm border border-slate-100 group-hover:border-cyan-100 transition-colors">
                              <Icon className="w-5 h-5" />
                            </div>
                            <div>
                              <h4 className="text-sm font-bold text-slate-900">{cat.label}</h4>
                              <p className="text-[11px] text-slate-500">{cat.description}</p>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-1">
                            {[1, 2, 3, 4, 5].map((star) => (
                              <button
                                key={star}
                                onMouseEnter={() => handleHoverRating(cat.id, star)}
                                onMouseLeave={() => handleHoverRating(cat.id, 0)}
                                onClick={() => handleSetRating(cat.id, star)}
                                className="p-1 transition-transform hover:scale-110 active:scale-95"
                              >
                                <Star 
                                  className={`w-6 h-6 ${
                                    star <= (currentHover || currentRating)
                                      ? 'text-amber-400 fill-amber-400'
                                      : 'text-slate-200'
                                  }`} 
                                />
                              </button>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">
                      Any specific thoughts?
                    </label>
                    <textarea
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      placeholder="What can we improve? What's working well? Bugs you've encountered? (Optional)"
                      rows={6}
                      className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:bg-white transition-all resize-none text-sm leading-relaxed"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Footer - Fixed at bottom of modal */}
            {!submitted && (
              <div className="px-8 py-6 border-t border-slate-100 shrink-0 bg-slate-50/50">
                {step === 1 ? (
                  <button
                    onClick={() => setStep(2)}
                    disabled={!isStep1Valid}
                    className="w-full py-4 bg-slate-900 text-white rounded-2xl font-bold hover:bg-slate-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg shadow-slate-200"
                  >
                    Continue
                    <ArrowRight className="w-4 h-4" />
                  </button>
                ) : (
                  <div className="space-y-4">
                    <div className="flex gap-3">
                      <button
                        onClick={() => setStep(1)}
                        className="px-6 bg-white border border-slate-200 text-slate-600 rounded-2xl font-bold hover:bg-slate-50 transition-all flex items-center justify-center gap-2"
                      >
                        <ChevronLeft className="w-4 h-4" />
                        Back
                      </button>
                      <button
                        onClick={() => mutation.mutate()}
                        disabled={mutation.isPending}
                        className="flex-1 py-4 bg-slate-900 text-white rounded-2xl font-bold hover:bg-slate-800 transition-all disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg shadow-slate-200"
                      >
                        {mutation.isPending ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          comment.trim() ? 'Submit Detailed Feedback' : 'Skip & Submit Ratings'
                        )}
                      </button>
                    </div>
                    {mutation.isError && (
                      <div className="flex items-center gap-2 text-rose-600 text-xs font-medium justify-center">
                        <AlertCircle className="w-4 h-4" />
                        Failed to submit. Please try again.
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}