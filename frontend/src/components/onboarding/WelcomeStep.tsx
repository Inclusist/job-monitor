import { motion } from 'framer-motion';
import { Sparkles, Target, BarChart3, Shield, ArrowRight } from 'lucide-react';

interface WelcomeStepProps {
    onNext: () => void;
    isFirstStep: boolean;
}

export default function WelcomeStep({ onNext }: WelcomeStepProps) {
    return (
        <div className="max-w-2xl mx-auto text-center">
            <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', duration: 0.6 }}
                className="w-20 h-20 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-2xl flex items-center justify-center mx-auto mb-8 shadow-lg"
            >
                <Sparkles className="w-10 h-10 text-white" />
            </motion.div>

            <h1 className="text-4xl font-bold text-slate-900 mb-4">
                Welcome to Inclusist!
            </h1>

            <p className="text-xl text-slate-600 mb-12">
                Let's get you set up in just a few minutes. We'll help you find jobs that truly match your skills and experience.
            </p>

            <div className="grid md:grid-cols-3 gap-6 mb-12">
                {[
                    {
                        icon: Target,
                        title: 'Upload Your CV',
                        description: 'Our AI analyzes your skills and experience'
                    },
                    {
                        icon: BarChart3,
                        title: 'Set Preferences',
                        description: 'Tell us what kind of work you\'re looking for'
                    },
                    {
                        icon: Shield,
                        title: 'Get Matches',
                        description: 'Receive personalized job recommendations daily'
                    }
                ].map((feature, index) => (
                    <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 + index * 0.1 }}
                        className="bg-white rounded-xl p-6 shadow-sm border border-slate-200"
                    >
                        <div className="w-12 h-12 bg-cyan-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                            <feature.icon className="w-6 h-6 text-cyan-600" />
                        </div>
                        <h3 className="font-semibold text-slate-900 mb-2">{feature.title}</h3>
                        <p className="text-sm text-slate-600">{feature.description}</p>
                    </motion.div>
                ))}
            </div>

            <button
                onClick={onNext}
                className="px-8 py-4 bg-cyan-600 text-white rounded-xl font-semibold hover:bg-cyan-700 transition-colors inline-flex items-center space-x-2 shadow-lg shadow-cyan-600/30"
            >
                <span>Get Started</span>
                <ArrowRight className="w-5 h-5" />
            </button>

            <p className="text-sm text-slate-500 mt-8">
                Takes about 3 minutes • Your data is secure and never shared
            </p>
        </div>
    );
}
