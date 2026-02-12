import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Upload, FileText, Loader2, CheckCircle2, AlertCircle, ArrowRight, ArrowLeft } from 'lucide-react';
import { uploadCV } from '../../services/profile';

interface UploadCVStepProps {
    onNext: (data?: any) => void;
    onBack: () => void;
    isFirstStep: boolean;
}

export default function UploadCVStep({ onNext, onBack }: UploadCVStepProps) {
    const [uploading, setUploading] = useState(false);
    const [uploaded, setUploaded] = useState(false);
    const [error, setError] = useState('');
    const [dragActive, setDragActive] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            handleFile(e.target.files[0]);
        }
    };

    const handleFile = async (file: File) => {
        setError('');
        setUploading(true);

        try {
            const result = await uploadCV(file, true, true);

            if (result.success) {
                setUploaded(true);
                // Auto-advance after 1 second
                setTimeout(() => {
                    onNext({ cvId: result.cv_id });
                }, 1000);
            } else {
                setError(result.error || 'Failed to upload CV');
            }
        } catch (err) {
            setError('An error occurred while uploading your CV');
        } finally {
            setUploading(false);
        }
    };

    const handleSkipForNow = () => {
        onNext({ skipped: true });
    };

    return (
        <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-slate-900 mb-3">
                    Upload Your CV
                </h2>
                <p className="text-lg text-slate-600">
                    We'll analyze your skills and experience to find the best matches
                </p>
            </div>

            {/* Upload Area */}
            <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`relative border-2 border-dashed rounded-2xl p-12 text-center transition-all ${dragActive
                    ? 'border-cyan-500 bg-cyan-50'
                    : uploaded
                        ? 'border-green-500 bg-green-50'
                        : error
                            ? 'border-red-500 bg-red-50'
                            : 'border-slate-300 bg-white hover:border-cyan-400'
                    }`}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.doc,.docx"
                    onChange={handleChange}
                    className="hidden"
                />

                {uploading ? (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="flex flex-col items-center"
                    >
                        <Loader2 className="w-16 h-16 text-cyan-600 animate-spin mb-4" />
                        <p className="text-lg font-medium text-slate-700">Analyzing your CV...</p>
                        <p className="text-sm text-slate-500 mt-2">This may take a minute</p>
                    </motion.div>
                ) : uploaded ? (
                    <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="flex flex-col items-center"
                    >
                        <CheckCircle2 className="w-16 h-16 text-green-600 mb-4" />
                        <p className="text-lg font-medium text-green-700">CV uploaded successfully!</p>
                        <p className="text-sm text-slate-500 mt-2">Moving to next step...</p>
                    </motion.div>
                ) : error ? (
                    <div className="flex flex-col items-center">
                        <AlertCircle className="w-16 h-16 text-red-600 mb-4" />
                        <p className="text-lg font-medium text-red-700 mb-2">Upload failed</p>
                        <p className="text-sm text-slate-600 mb-4">{error}</p>
                        <button
                            onClick={() => {
                                setError('');
                                fileInputRef.current?.click();
                            }}
                            className="px-6 py-2 bg-cyan-600 text-white rounded-lg font-medium hover:bg-cyan-700 transition-colors"
                        >
                            Try Again
                        </button>
                    </div>
                ) : (
                    <div className="flex flex-col items-center">
                        <div className="w-16 h-16 bg-cyan-100 rounded-full flex items-center justify-center mb-4">
                            <Upload className="w-8 h-8 text-cyan-600" />
                        </div>
                        <p className="text-lg font-medium text-slate-700 mb-2">
                            Drop your CV here or click to browse
                        </p>
                        <p className="text-sm text-slate-500 mb-6">
                            Supports PDF, DOC, DOCX (max 10MB)
                        </p>
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            className="px-6 py-3 bg-cyan-600 text-white rounded-xl font-semibold hover:bg-cyan-700 transition-colors inline-flex items-center space-x-2"
                        >
                            <FileText className="w-5 h-5" />
                            <span>Choose File</span>
                        </button>
                    </div>
                )}
            </div>

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
                    onClick={handleSkipForNow}
                    className="text-sm text-slate-500 hover:text-slate-700 transition-colors"
                >
                    I'll upload later
                </button>
            </div>
        </div>
    );
}
