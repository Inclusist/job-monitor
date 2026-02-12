import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, Pencil, Loader2, ArrowRight, ArrowLeft } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getProfile } from '../../services/profile';

interface ReviewProfileStepProps {
    onNext: () => void;
    onBack: () => void;
    stepData: Record<string, any>;
}

export default function ReviewProfileStep({ onNext, onBack, stepData }: ReviewProfileStepProps) {
    const { data: profile, isLoading } = useQuery({
        queryKey: ['profile'],
        queryFn: getProfile,
    });

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 text-cyan-600 animate-spin" />
            </div>
        );
    }

    const cvProfile = profile?.profile;
    const hasProfile = cvProfile && Object.keys(cvProfile).length > 0;

    return (
        <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-slate-900 mb-3">
                    Review Your Profile
                </h2>
                <p className="text-lg text-slate-600">
                    Here's what we extracted from your CV. You can edit this later in your profile.
                </p>
            </div>

            {hasProfile ? (
                <div className="space-y-6">
                    {/* Skills */}
                    {cvProfile.technical_skills && cvProfile.technical_skills.length > 0 && (
                        <div className="bg-white rounded-xl p-6 border border-slate-200">
                            <h3 className="font-semibold text-slate-900 mb-3 flex items-center">
                                <CheckCircle2 className="w-5 h-5 text-green-600 mr-2" />
                                Technical Skills
                            </h3>
                            <div className="flex flex-wrap gap-2">
                                {cvProfile.technical_skills.slice(0, 10).map((skill: string, index: number) => (
                                    <span
                                        key={index}
                                        className="px-3 py-1 bg-cyan-100 text-cyan-700 rounded-lg text-sm font-medium"
                                    >
                                        {skill}
                                    </span>
                                ))}
                                {cvProfile.technical_skills.length > 10 && (
                                    <span className="px-3 py-1 bg-slate-100 text-slate-600 rounded-lg text-sm">
                                        +{cvProfile.technical_skills.length - 10} more
                                    </span>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Experience Summary */}
                    {cvProfile.expertise_summary && (
                        <div className="bg-white rounded-xl p-6 border border-slate-200">
                            <h3 className="font-semibold text-slate-900 mb-3 flex items-center">
                                <CheckCircle2 className="w-5 h-5 text-green-600 mr-2" />
                                Experience Summary
                            </h3>
                            <p className="text-slate-700">{cvProfile.expertise_summary}</p>
                        </div>
                    )}

                    {/* Work History */}
                    {cvProfile.work_experience && cvProfile.work_experience.length > 0 && (
                        <div className="bg-white rounded-xl p-6 border border-slate-200">
                            <h3 className="font-semibold text-slate-900 mb-3 flex items-center">
                                <CheckCircle2 className="w-5 h-5 text-green-600 mr-2" />
                                Recent Experience
                            </h3>
                            <div className="space-y-3">
                                {cvProfile.work_experience.slice(0, 2).map((exp: any, index: number) => (
                                    <div key={index} className="border-l-2 border-cyan-600 pl-4">
                                        <p className="font-medium text-slate-900">{exp.title || exp.role}</p>
                                        <p className="text-sm text-slate-600">{exp.company}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="bg-cyan-50 rounded-xl p-4 border border-cyan-200">
                        <p className="text-sm text-cyan-800">
                            <Pencil className="w-4 h-4 inline mr-2" />
                            You can edit and refine your profile anytime from the Profile page
                        </p>
                    </div>
                </div>
            ) : (
                <div className="bg-white rounded-xl p-12 text-center border border-slate-200">
                    <p className="text-slate-600 mb-4">
                        No CV uploaded yet. You can upload one later to get better matches.
                    </p>
                </div>
            )}

            {/* Navigation */}
            <div className="flex items-center justify-between mt-8">
                <button
                    onClick={onBack}
                    className="px-6 py-3 text-slate-600 hover:text-slate-900 font-medium inline-flex items-center space-x-2 transition-colors"
                >
                    <ArrowLeft className="w-5 h-5" />
                    <span>Back</span>
                </button>

                <button
                    onClick={onNext}
                    className="px-8 py-3 bg-cyan-600 text-white rounded-xl font-semibold hover:bg-cyan-700 transition-colors inline-flex items-center space-x-2"
                >
                    <span>Continue</span>
                    <ArrowRight className="w-5 h-5" />
                </button>
            </div>
        </div>
    );
}
