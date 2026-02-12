import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Sparkles, CheckCircle2 } from 'lucide-react';

interface CompletionStepProps {
    onNext: () => void;
}

export default function CompletionStep({ onNext }: CompletionStepProps) {
    const navigate = useNavigate();
    const calledRef = useRef(false);

    useEffect(() => {
        // Mark onboarding as complete — call only once
        if (!calledRef.current) {
            calledRef.current = true;
            onNext();
        }

        // Auto-redirect after 3 seconds
        const timer = setTimeout(() => {
            navigate('/jobs');
        }, 3000);

        return () => clearTimeout(timer);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    return (
        <div className="max-w-2xl mx-auto text-center py-12">
            <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', duration: 0.6 }}
                className="relative mx-auto mb-8"
            >
                <div className="w-32 h-32 bg-gradient-to-br from-green-500 to-green-600 rounded-full flex items-center justify-center mx-auto shadow-2xl">
                    <CheckCircle2 className="w-16 h-16 text-white" />
                </div>

                {/* Confetti effect */}
                {[...Array(12)].map((_, i) => (
                    <motion.div
                        key={i}
                        initial={{ scale: 0, x: 0, y: 0 }}
                        animate={{
                            scale: [0, 1, 0],
                            x: Math.cos((i * 30 * Math.PI) / 180) * 100,
                            y: Math.sin((i * 30 * Math.PI) / 180) * 100,
                        }}
                        transition={{ duration: 1, delay: 0.2 }}
                        className="absolute top-1/2 left-1/2 w-3 h-3 bg-cyan-500 rounded-full"
                        style={{
                            backgroundColor: ['#06b6d4', '#10b981', '#f59e0b', '#ec4899'][i % 4],
                        }}
                    />
                ))}
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
            >
                <h1 className="text-4xl font-bold text-slate-900 mb-4">
                    You're All Set! 🎉
                </h1>

                <p className="text-xl text-slate-600 mb-8">
                    We're finding your perfect job matches right now
                </p>

                <div className="bg-white rounded-xl p-8 border border-slate-200 shadow-sm mb-8">
                    <div className="flex items-center justify-center space-x-8">
                        <div className="text-center">
                            <div className="w-12 h-12 bg-cyan-100 rounded-full flex items-center justify-center mx-auto mb-2">
                                <Sparkles className="w-6 h-6 text-cyan-600" />
                            </div>
                            <p className="text-sm font-medium text-slate-700">AI Matching</p>
                            <p className="text-xs text-slate-500">Active</p>
                        </div>
                        <div className="text-center">
                            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-2">
                                <CheckCircle2 className="w-6 h-6 text-green-600" />
                            </div>
                            <p className="text-sm font-medium text-slate-700">Profile</p>
                            <p className="text-xs text-slate-500">Complete</p>
                        </div>
                    </div>
                </div>

                <p className="text-sm text-slate-500">
                    Redirecting to your matches in a moment...
                </p>
            </motion.div>
        </div>
    );
}
