import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
    Target,
    Upload,
    CheckCircle2,
    Settings,
    Sparkles,
    X,
    Loader2
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import {
    getOnboardingStatus,
    updateOnboardingStep,
    completeOnboarding,
    skipOnboarding
} from '../services/onboarding';

// Import step components
import WelcomeStep from '../components/onboarding/WelcomeStep';
import UploadCVStep from '../components/onboarding/UploadCVStep';
import ReviewProfileStep from '../components/onboarding/ReviewProfileStep';
import SetPreferencesStep from '../components/onboarding/SetPreferencesStep';
import MatchingProgressStep from '../components/onboarding/MatchingProgressStep';
import CompletionStep from '../components/onboarding/CompletionStep';

const STEPS = [
    { id: 0, title: 'Welcome', icon: Sparkles, component: WelcomeStep },
    { id: 1, title: 'Upload CV', icon: Upload, component: UploadCVStep },
    { id: 2, title: 'Review Profile', icon: CheckCircle2, component: ReviewProfileStep },
    { id: 3, title: 'Set Preferences', icon: Settings, component: SetPreferencesStep },
    { id: 4, title: 'Finding Matches', icon: Loader2, component: MatchingProgressStep },
    { id: 5, title: 'Complete', icon: Target, component: CompletionStep },
];

export default function OnboardingPage() {
    const navigate = useNavigate();
    const { refreshAuth } = useAuth();
    const [currentStep, setCurrentStep] = useState(0);
    const [loading, setLoading] = useState(true);
    const [showSkipDialog, setShowSkipDialog] = useState(false);
    const [stepData, setStepData] = useState<Record<string, any>>({});

    useEffect(() => {
        loadOnboardingStatus();
    }, []);

    const loadOnboardingStatus = async () => {
        try {
            const status = await getOnboardingStatus();

            // If already completed, redirect to jobs
            if (status.onboarding_completed) {
                navigate('/jobs');
                return;
            }

            // Resume from saved step
            setCurrentStep(status.onboarding_step || 0);
        } catch (error) {
            console.error('Error loading onboarding status:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleNext = async (data?: any) => {
        // Save step data
        if (data) {
            setStepData(prev => ({ ...prev, [`step_${currentStep}`]: data }));
        }

        const nextStep = currentStep + 1;

        // Update backend
        await updateOnboardingStep(nextStep);

        // If this is the last step, mark as complete
        if (nextStep >= STEPS.length) {
            await completeOnboarding();
            await refreshAuth();
            // CompletionStep will handle redirect
        } else {
            setCurrentStep(nextStep);
        }
    };

    const handleBack = () => {
        if (currentStep > 0) {
            const prevStep = currentStep - 1;
            setCurrentStep(prevStep);
            updateOnboardingStep(prevStep);
        }
    };

    const handleSkip = async () => {
        try {
            await skipOnboarding();
            await refreshAuth();
            navigate('/jobs');
        } catch (error) {
            console.error('Error skipping onboarding:', error);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-white to-cyan-50">
                <Loader2 className="w-8 h-8 text-cyan-600 animate-spin" />
            </div>
        );
    }

    const CurrentStepComponent = STEPS[currentStep].component;
    const isLastStep = currentStep === STEPS.length - 1;
    const isFirstStep = currentStep === 0;

    return (
        <div className="min-h-screen bg-gradient-to-b from-white to-cyan-50">
            {/* Header */}
            <div className="bg-white border-b border-slate-200">
                <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                        <Target className="w-6 h-6 text-cyan-600" />
                        <span className="text-xl font-semibold text-slate-900">Inclusist</span>
                    </div>

                    {!isLastStep && (
                        <button
                            onClick={() => setShowSkipDialog(true)}
                            className="text-sm text-slate-500 hover:text-slate-700 transition-colors"
                        >
                            Skip for now
                        </button>
                    )}
                </div>
            </div>

            {/* Progress Bar */}
            {!isLastStep && (
                <div className="bg-white border-b border-slate-200">
                    <div className="max-w-4xl mx-auto px-6 py-6">
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-sm font-medium text-slate-700">
                                Step {currentStep + 1} of {STEPS.length}
                            </span>
                            <span className="text-sm text-slate-500">
                                {STEPS[currentStep].title}
                            </span>
                        </div>

                        <div className="flex space-x-2">
                            {STEPS.map((step, index) => (
                                <div
                                    key={step.id}
                                    className={`h-2 flex-1 rounded-full transition-all ${index <= currentStep
                                        ? 'bg-cyan-600'
                                        : 'bg-slate-200'
                                        }`}
                                />
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Step Content */}
            <div className="max-w-4xl mx-auto px-6 py-12">
                <AnimatePresence mode="wait">
                    <motion.div
                        key={currentStep}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.3 }}
                    >
                        <CurrentStepComponent
                            onNext={handleNext}
                            onBack={handleBack}
                            stepData={stepData}
                            isFirstStep={isFirstStep}
                            isLastStep={isLastStep}
                        />
                    </motion.div>
                </AnimatePresence>
            </div>

            {/* Skip Confirmation Dialog */}
            {showSkipDialog && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl"
                    >
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-slate-900">Skip setup?</h3>
                            <button
                                onClick={() => setShowSkipDialog(false)}
                                className="text-slate-400 hover:text-slate-600"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <p className="text-slate-600 mb-6">
                            Completing the setup helps us find better job matches for you. You can always finish it later from your profile.
                        </p>

                        <div className="flex space-x-3">
                            <button
                                onClick={() => setShowSkipDialog(false)}
                                className="flex-1 px-4 py-2 border-2 border-slate-300 text-slate-700 rounded-xl font-semibold hover:bg-slate-50 transition-colors"
                            >
                                Continue Setup
                            </button>
                            <button
                                onClick={handleSkip}
                                className="flex-1 px-4 py-2 bg-slate-600 text-white rounded-xl font-semibold hover:bg-slate-700 transition-colors"
                            >
                                Skip Anyway
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </div>
    );
}
