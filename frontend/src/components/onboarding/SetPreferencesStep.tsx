import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Settings, MapPin, Briefcase, Home, ArrowRight, ArrowLeft, Loader2, Sparkles, Check, X } from 'lucide-react';
import { useQuery, useMutation } from '@tanstack/react-query';
import api from '../../services/api';
import { getSearchQueries } from '../../services/searchQueries';
import { generatePreferences } from '../../services/generatePreferences';

interface SetPreferencesStepProps {
    onNext: () => void;
    onBack: () => void;
}

const WORK_ARRANGEMENTS = [
    { value: 'remote', label: 'Remote', icon: Home },
    { value: 'hybrid', label: 'Hybrid', icon: Briefcase },
    { value: 'onsite', label: 'On-site', icon: MapPin },
];

export default function SetPreferencesStep({ onNext, onBack }: SetPreferencesStepProps) {
    const [jobTitles, setJobTitles] = useState('');
    const [country, setCountry] = useState('');
    const [cities, setCities] = useState('');
    const [workArrangement, setWorkArrangement] = useState<string[]>([]);
    const [saving, setSaving] = useState(false);

    // Fetch search queries to prefill from auto-generated queries
    const { data: searchQueries, isLoading } = useQuery({
        queryKey: ['searchQueries'],
        queryFn: getSearchQueries,
    });

    const [showSuggestions, setShowSuggestions] = useState(false);
    const [suggestions, setSuggestions] = useState<{
        job_titles: {
            current_level: string[];
            advancement: string[];
            career_pivot: string[];
        };
        country: string;
        cities: string[];
        work_arrangement: string;
    } | null>(null);

    // AI generation mutation
    const generateMutation = useMutation({
        mutationFn: generatePreferences,
        onSuccess: (data) => {
            setSuggestions(data);
            setShowSuggestions(true);
        },
    });

    const acceptSuggestion = (type: 'title' | 'country' | 'city', value: string) => {
        if (type === 'title') {
            const current = jobTitles.split(',').map(s => s.trim()).filter(Boolean);
            if (!current.includes(value)) {
                setJobTitles(current.concat(value).join(', '));
            }
            // Remove from whichever category it belongs to
            setSuggestions(prev => prev ? {
                ...prev,
                job_titles: {
                    current_level: prev.job_titles.current_level.filter(t => t !== value),
                    advancement: prev.job_titles.advancement.filter(t => t !== value),
                    career_pivot: prev.job_titles.career_pivot.filter(t => t !== value),
                }
            } : null);
        } else if (type === 'country') {
            setCountry(value);
            setSuggestions(prev => prev ? {
                ...prev,
                country: ''
            } : null);
        } else {
            const current = cities.split(',').map(s => s.trim()).filter(Boolean);
            if (!current.includes(value)) {
                setCities(current.concat(value).join(', '));
            }
            setSuggestions(prev => prev ? {
                ...prev,
                cities: prev.cities.filter(l => l !== value)
            } : null);
        }
    };

    const declineSuggestion = (type: 'title' | 'country' | 'city', value: string) => {
        setSuggestions(prev => prev ? {
            ...prev,
            job_titles: type === 'title' ? {
                current_level: prev.job_titles.current_level.filter(t => t !== value),
                advancement: prev.job_titles.advancement.filter(t => t !== value),
                career_pivot: prev.job_titles.career_pivot.filter(t => t !== value),
            } : prev.job_titles,
            country: type === 'country' ? '' : prev.country,
            cities: type === 'city' ? prev.cities.filter(l => l !== value) : prev.cities
        } : null);
    };

    const acceptWorkArrangement = (value: string) => {
        const arrangement = value.toLowerCase();
        if (['remote', 'hybrid', 'onsite'].includes(arrangement)) {
            setWorkArrangement([arrangement]);
        }
        setSuggestions(prev => prev ? { ...prev, work_arrangement: '' } : null);
    };

    // Prefill from search queries when they load
    useEffect(() => {
        if (searchQueries) {
            if (searchQueries.titles && searchQueries.titles.length > 0) {
                setJobTitles(searchQueries.titles.join(', '));
            }

            if (searchQueries.locations && searchQueries.locations.length > 0) {
                const locs = searchQueries.locations as string[];
                // Parse "City, Country" format locations
                const parsedCities: string[] = [];
                let detectedCountry = '';

                for (const loc of locs) {
                    if (loc.toLowerCase() === 'remote') continue; // handled by work arrangement
                    const parts = loc.split(',').map(s => s.trim());
                    if (parts.length === 2) {
                        // "City, Country" format
                        parsedCities.push(parts[0]);
                        if (!detectedCountry) detectedCountry = parts[1];
                    } else {
                        // Bare location — could be country or city
                        parsedCities.push(loc);
                    }
                }

                if (detectedCountry) setCountry(detectedCountry);
                if (parsedCities.length > 0) setCities(parsedCities.join(', '));

                // If remote was in locations, ensure work arrangement reflects it
                if (locs.some(l => l.toLowerCase() === 'remote')) {
                    setWorkArrangement(prev => prev.includes('remote') ? prev : [...prev, 'remote']);
                }
            }

            if (searchQueries.work_arrangement) {
                const arrangement = searchQueries.work_arrangement.toLowerCase();
                if (['remote', 'hybrid', 'onsite'].includes(arrangement)) {
                    setWorkArrangement([arrangement]);
                }
            }
        }
    }, [searchQueries]);

    const toggleWorkArrangement = (value: string) => {
        setWorkArrangement(prev =>
            prev.includes(value)
                ? prev.filter(v => v !== value)
                : [...prev, value]
        );
    };

    const handleContinue = async () => {
        setSaving(true);

        try {
            const keywords = jobTitles.split(',').map(s => s.trim()).filter(Boolean);
            const cityList = cities.split(',').map(s => s.trim()).filter(Boolean);
            const countryName = country.trim();

            // Format locations as "City, Country" for each city
            const locations: string[] = [];
            if (cityList.length > 0 && countryName) {
                for (const city of cityList) {
                    locations.push(`${city}, ${countryName}`);
                }
            } else if (cityList.length > 0) {
                // Cities without country — use as-is
                locations.push(...cityList);
            } else if (countryName) {
                // Country only, no cities
                locations.push(countryName);
            }

            // Add "Remote" as a location if remote work is selected
            if (workArrangement.includes('remote')) {
                locations.push('Remote');
            }

            await api.post('/api/update-search-preferences', {
                keywords,
                locations,
                work_arrangements: workArrangement,
            });

            onNext();
        } catch (error) {
            console.error('Error saving preferences:', error);
            onNext();
        } finally {
            setSaving(false);
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 text-cyan-600 animate-spin" />
            </div>
        );
    }

    return (
        <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-slate-900 mb-3">
                    Set Your Preferences
                </h2>
                <p className="text-lg text-slate-600">
                    {searchQueries?.query_count ? 'Review and adjust your auto-generated preferences' : 'Tell us what kind of work you\'re looking for'}
                </p>
            </div>

            <div className="space-y-6">
                {/* AI Generate Button */}
                <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-xl p-4">
                    <div className="flex items-center justify-between gap-4">
                        <div className="flex-1">
                            <h3 className="font-semibold text-slate-900 mb-1">Need help filling this out?</h3>
                            <p className="text-sm text-slate-600">Let AI analyze your CV and suggest relevant job titles and locations</p>
                        </div>
                        <button
                            type="button"
                            onClick={() => generateMutation.mutate()}
                            disabled={generateMutation.isPending}
                            className="px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 whitespace-nowrap shrink-0"
                        >
                            {generateMutation.isPending ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Generating...
                                </>
                            ) : (
                                <>
                                    <Sparkles className="w-4 h-4" />
                                    Generate with AI
                                </>
                            )}
                        </button>
                    </div>
                    {generateMutation.isError && (
                        <p className="mt-2 text-sm text-red-600">Failed to generate suggestions. Please try again.</p>
                    )}

                    {/* Suggestions Area */}
                    {showSuggestions && suggestions && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            className="mt-6 space-y-4 border-t border-purple-100 pt-4"
                        >
                            <div className="flex items-center justify-between mb-2">
                                <h4 className="text-sm font-semibold text-purple-900 flex items-center gap-2">
                                    <Sparkles className="w-4 h-4" />
                                    AI Suggestions
                                </h4>
                                <button
                                    onClick={() => setShowSuggestions(false)}
                                    className="text-xs text-purple-600 hover:text-purple-800 font-medium"
                                >
                                    Dismiss all
                                </button>
                            </div>

                            {/* Job Title Suggestions - Categorized */}
                            {suggestions.job_titles.current_level.length > 0 && (
                                <div>
                                    <p className="text-xs font-medium text-slate-500 mb-2 uppercase tracking-wider">Similar Roles</p>
                                    <div className="flex flex-wrap gap-2">
                                        {suggestions.job_titles.current_level.map(title => (
                                            <div key={title} className="flex items-center gap-1 bg-white border border-purple-200 rounded-full pl-3 pr-1 py-1 shadow-sm">
                                                <span className="text-sm text-slate-700">{title}</span>
                                                <div className="flex items-center gap-1">
                                                    <button
                                                        onClick={() => acceptSuggestion('title', title)}
                                                        className="p-1 hover:bg-green-50 text-green-600 rounded-full transition-colors"
                                                        title="Accept"
                                                    >
                                                        <Check className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button
                                                        onClick={() => declineSuggestion('title', title)}
                                                        className="p-1 hover:bg-red-50 text-red-400 rounded-full transition-colors"
                                                        title="Decline"
                                                    >
                                                        <X className="w-3.5 h-3.5" />
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {suggestions.job_titles.advancement.length > 0 && (
                                <div>
                                    <p className="text-xs font-medium text-slate-500 mb-2 uppercase tracking-wider">Career Advancement</p>
                                    <div className="flex flex-wrap gap-2">
                                        {suggestions.job_titles.advancement.map(title => (
                                            <div key={title} className="flex items-center gap-1 bg-white border border-purple-200 rounded-full pl-3 pr-1 py-1 shadow-sm">
                                                <span className="text-sm text-slate-700">{title}</span>
                                                <div className="flex items-center gap-1">
                                                    <button
                                                        onClick={() => acceptSuggestion('title', title)}
                                                        className="p-1 hover:bg-green-50 text-green-600 rounded-full transition-colors"
                                                        title="Accept"
                                                    >
                                                        <Check className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button
                                                        onClick={() => declineSuggestion('title', title)}
                                                        className="p-1 hover:bg-red-50 text-red-400 rounded-full transition-colors"
                                                        title="Decline"
                                                    >
                                                        <X className="w-3.5 h-3.5" />
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {suggestions.job_titles.career_pivot.length > 0 && (
                                <div>
                                    <p className="text-xs font-medium text-slate-500 mb-2 uppercase tracking-wider">Alternative Paths</p>
                                    <div className="flex flex-wrap gap-2">
                                        {suggestions.job_titles.career_pivot.map(title => (
                                            <div key={title} className="flex items-center gap-1 bg-white border border-purple-200 rounded-full pl-3 pr-1 py-1 shadow-sm">
                                                <span className="text-sm text-slate-700">{title}</span>
                                                <div className="flex items-center gap-1">
                                                    <button
                                                        onClick={() => acceptSuggestion('title', title)}
                                                        className="p-1 hover:bg-green-50 text-green-600 rounded-full transition-colors"
                                                        title="Accept"
                                                    >
                                                        <Check className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button
                                                        onClick={() => declineSuggestion('title', title)}
                                                        className="p-1 hover:bg-red-50 text-red-400 rounded-full transition-colors"
                                                        title="Decline"
                                                    >
                                                        <X className="w-3.5 h-3.5" />
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Country Suggestions */}
                            {suggestions.country && (
                                <div>
                                    <p className="text-xs font-medium text-slate-500 mb-2 uppercase tracking-wider">Suggested Country</p>
                                    <div className="flex flex-wrap gap-2">
                                        <div className="flex items-center gap-1 bg-white border border-purple-200 rounded-full pl-3 pr-1 py-1 shadow-sm">
                                            <span className="text-sm text-slate-700">{suggestions.country}</span>
                                            <div className="flex items-center gap-1">
                                                <button
                                                    onClick={() => acceptSuggestion('country', suggestions.country)}
                                                    className="p-1 hover:bg-green-50 text-green-600 rounded-full transition-colors"
                                                    title="Accept"
                                                >
                                                    <Check className="w-3.5 h-3.5" />
                                                </button>
                                                <button
                                                    onClick={() => declineSuggestion('country', suggestions.country)}
                                                    className="p-1 hover:bg-red-50 text-red-400 rounded-full transition-colors"
                                                    title="Decline"
                                                >
                                                    <X className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* City Suggestions */}
                            {suggestions.cities.length > 0 && (
                                <div>
                                    <p className="text-xs font-medium text-slate-500 mb-2 uppercase tracking-wider">Suggested Cities</p>
                                    <div className="flex flex-wrap gap-2">
                                        {suggestions.cities.map(city => (
                                            <div key={city} className="flex items-center gap-1 bg-white border border-purple-200 rounded-full pl-3 pr-1 py-1 shadow-sm">
                                                <span className="text-sm text-slate-700">{city}</span>
                                                <div className="flex items-center gap-1">
                                                    <button
                                                        onClick={() => acceptSuggestion('city', city)}
                                                        className="p-1 hover:bg-green-50 text-green-600 rounded-full transition-colors"
                                                        title="Accept"
                                                    >
                                                        <Check className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button
                                                        onClick={() => declineSuggestion('city', city)}
                                                        className="p-1 hover:bg-red-50 text-red-400 rounded-full transition-colors"
                                                        title="Decline"
                                                    >
                                                        <X className="w-3.5 h-3.5" />
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Work Arrangement Suggestion */}
                            {suggestions.work_arrangement && (
                                <div>
                                    <p className="text-xs font-medium text-slate-500 mb-2 uppercase tracking-wider">Suggested Arrangement</p>
                                    <div className="flex flex-wrap gap-2">
                                        <div className="flex items-center gap-1 bg-white border border-purple-200 rounded-full pl-3 pr-1 py-1 shadow-sm">
                                            <span className="text-sm text-slate-700 capitalize">{suggestions.work_arrangement}</span>
                                            <div className="flex items-center gap-1">
                                                <button
                                                    onClick={() => acceptWorkArrangement(suggestions.work_arrangement)}
                                                    className="p-1 hover:bg-green-50 text-green-600 rounded-full transition-colors"
                                                    title="Accept"
                                                >
                                                    <Check className="w-3.5 h-3.5" />
                                                </button>
                                                <button
                                                    onClick={() => setSuggestions(prev => prev ? { ...prev, work_arrangement: '' } : null)}
                                                    className="p-1 hover:bg-red-50 text-red-400 rounded-full transition-colors"
                                                    title="Decline"
                                                >
                                                    <X className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </motion.div>
                    )}
                </div>

                {/* Job Titles */}
                <div className="bg-white rounded-xl p-6 border border-slate-200">
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                        <Briefcase className="w-4 h-4 inline mr-2" />
                        Job Titles
                    </label>
                    <input
                        type="text"
                        value={jobTitles}
                        onChange={(e) => setJobTitles(e.target.value)}
                        placeholder="e.g. Software Engineer, Full Stack Developer"
                        className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                    />
                    <p className="text-xs text-slate-500 mt-2">
                        Separate multiple titles with commas
                    </p>
                </div>

                {/* Country and Cities */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-white rounded-xl p-6 border border-slate-200">
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            <MapPin className="w-4 h-4 inline mr-2 text-cyan-600" />
                            Country
                        </label>
                        <input
                            type="text"
                            value={country}
                            onChange={(e) => setCountry(e.target.value)}
                            placeholder="e.g. Germany"
                            className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                        />
                    </div>
                    <div className="bg-white rounded-xl p-6 border border-slate-200">
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            <MapPin className="w-4 h-4 inline mr-2 text-cyan-600" />
                            Cities
                        </label>
                        <input
                            type="text"
                            value={cities}
                            onChange={(e) => setCities(e.target.value)}
                            placeholder="e.g. Berlin, Hamburg"
                            className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                        />
                    </div>
                </div>

                {/* Work Arrangement */}
                <div className="bg-white rounded-xl p-6 border border-slate-200">
                    <label className="block text-sm font-medium text-slate-700 mb-4">
                        <Settings className="w-4 h-4 inline mr-2" />
                        Work Arrangement
                    </label>
                    <div className="grid grid-cols-3 gap-3">
                        {WORK_ARRANGEMENTS.map((arrangement) => (
                            <button
                                key={arrangement.value}
                                onClick={() => toggleWorkArrangement(arrangement.value)}
                                className={`p-4 rounded-lg border-2 transition-all ${workArrangement.includes(arrangement.value)
                                    ? 'border-cyan-600 bg-cyan-50'
                                    : 'border-slate-200 hover:border-slate-300'
                                    }`}
                            >
                                <arrangement.icon className={`w-6 h-6 mx-auto mb-2 ${workArrangement.includes(arrangement.value)
                                    ? 'text-cyan-600'
                                    : 'text-slate-400'
                                    }`} />
                                <p className={`text-sm font-medium ${workArrangement.includes(arrangement.value)
                                    ? 'text-cyan-900'
                                    : 'text-slate-700'
                                    }`}>
                                    {arrangement.label}
                                </p>
                            </button>
                        ))}
                    </div>
                    <p className="text-xs text-slate-500 mt-3">
                        Select all that apply
                    </p>
                </div>
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-between mt-8">
                <button
                    onClick={onBack}
                    disabled={saving}
                    className="px-6 py-3 text-slate-600 hover:text-slate-900 font-medium inline-flex items-center space-x-2 transition-colors disabled:opacity-50"
                >
                    <ArrowLeft className="w-5 h-5" />
                    <span>Back</span>
                </button>

                <button
                    onClick={handleContinue}
                    disabled={saving}
                    className="px-8 py-3 bg-cyan-600 text-white rounded-xl font-semibold hover:bg-cyan-700 transition-colors inline-flex items-center space-x-2 disabled:opacity-50"
                >
                    <span>{saving ? 'Saving...' : 'Find My Matches'}</span>
                    <ArrowRight className="w-5 h-5" />
                </button>
            </div>
        </div>
    );
}
