import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Settings, Briefcase, MapPin, Home, Loader2, Check, Globe } from 'lucide-react';
import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';
import api from '../services/api';

const cardClass = 'border border-cyan-200 rounded-2xl p-8 bg-white shadow-sm';
const btnPrimary = 'px-6 py-2.5 bg-cyan-600 text-white rounded-xl font-semibold hover:bg-cyan-500 transition-colors text-sm';

interface SearchPreferences {
  keywords: string[];
  locations: string[];
  work_arrangements: string[];
}

const WORK_ARRANGEMENTS = [
  { value: 'remote', label: 'Remote', icon: Home },
  { value: 'hybrid', label: 'Hybrid', icon: Briefcase },
  { value: 'onsite', label: 'On-site', icon: MapPin },
];

async function fetchPreferences(): Promise<SearchPreferences> {
  const { data } = await api.get<SearchPreferences>('/api/search-preferences');
  return data;
}

/** Parse "City, Country" formatted locations into country + cities */
function parseLocations(locations: string[]): { country: string; cities: string[] } {
  const cities: string[] = [];
  let country = '';

  for (const loc of locations) {
    if (loc.toLowerCase() === 'remote') continue; // handled by work arrangement
    const parts = loc.split(',').map((s) => s.trim());
    if (parts.length === 2) {
      // "City, Country" format
      cities.push(parts[0]);
      if (!country) country = parts[1];
    } else {
      // Bare location — could be country or city
      cities.push(loc);
    }
  }

  return { country, cities };
}

export default function PreferencesPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['searchPreferences'],
    queryFn: fetchPreferences,
  });

  const [jobTitles, setJobTitles] = useState('');
  const [country, setCountry] = useState('');
  const [cities, setCities] = useState('');
  const [workArrangements, setWorkArrangements] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    if (data) {
      setJobTitles(data.keywords.join(', '));

      // Parse "City, Country" locations into separate fields
      const parsed = parseLocations(data.locations);
      setCountry(parsed.country);
      setCities(parsed.cities.join(', '));

      // Load work arrangements
      setWorkArrangements(data.work_arrangements || []);

      // If "Remote" was stored as a location, reflect it in work arrangements
      if (data.locations.some((l) => l.toLowerCase() === 'remote')) {
        setWorkArrangements((prev) => prev.includes('remote') ? prev : [...prev, 'remote']);
      }
    }
  }, [data]);

  const toggleWorkArrangement = (value: string) => {
    setWorkArrangements((prev) =>
      prev.includes(value)
        ? prev.filter((v) => v !== value)
        : [...prev, value]
    );
  };

  const handleSave = async () => {
    setSaving(true);
    setFeedback(null);
    try {
      const keywords = jobTitles.split(',').map((s) => s.trim()).filter(Boolean);
      const cityList = cities.split(',').map((s) => s.trim()).filter(Boolean);
      const countryName = country.trim();

      // Format locations as "City, Country" pairs
      const locations: string[] = [];
      if (cityList.length > 0 && countryName) {
        for (const city of cityList) {
          locations.push(`${city}, ${countryName}`);
        }
      } else if (cityList.length > 0) {
        locations.push(...cityList);
      } else if (countryName) {
        locations.push(countryName);
      }

      // Add "Remote" as a location if remote work is selected
      if (workArrangements.includes('remote')) {
        locations.push('Remote');
      }

      await api.post('/api/update-search-preferences', {
        keywords,
        locations,
        work_arrangements: workArrangements,
      });

      setFeedback({ type: 'success', message: 'Preferences saved successfully.' });
    } catch {
      setFeedback({ type: 'error', message: 'Failed to save preferences. Please try again.' });
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-cyan-50">
        <Header />
        <div className="pt-28 flex justify-center">
          <Loader2 className="w-8 h-8 text-cyan-600 animate-spin" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-cyan-50">
        <Header />
        <div className="pt-28 max-w-2xl mx-auto px-6">
          <p className="text-red-600">Failed to load preferences.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-cyan-50">
      <Header />
      <motion.main
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="pt-28 pb-16 max-w-2xl mx-auto px-6 space-y-8"
      >
        <h1 className="text-3xl font-bold text-slate-900">Search Preferences</h1>

        <div className={cardClass}>
          <div className="space-y-6">
            {/* Job Titles */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                <Briefcase className="w-4 h-4 inline mr-2 text-cyan-600" />
                Job Titles
              </label>
              <input
                type="text"
                value={jobTitles}
                onChange={(e) => setJobTitles(e.target.value)}
                placeholder="e.g. Software Engineer, Full Stack Developer"
                className="w-full px-4 py-3 border border-cyan-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-400 text-sm text-slate-900"
              />
              <p className="text-xs text-slate-500 mt-1.5">Separate multiple titles with commas</p>
            </div>

            {/* Location — Country + Cities */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                <MapPin className="w-4 h-4 inline mr-2 text-cyan-600" />
                Location
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Globe className="w-3.5 h-3.5 text-slate-400" />
                    <span className="text-xs font-medium text-slate-500">Country</span>
                  </div>
                  <input
                    type="text"
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    placeholder="e.g. Germany"
                    className="w-full px-4 py-3 border border-cyan-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-400 text-sm text-slate-900"
                  />
                </div>
                <div>
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    <span className="text-xs font-medium text-slate-500">Cities</span>
                  </div>
                  <input
                    type="text"
                    value={cities}
                    onChange={(e) => setCities(e.target.value)}
                    placeholder="e.g. Berlin, Hamburg"
                    className="w-full px-4 py-3 border border-cyan-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-400 text-sm text-slate-900"
                  />
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-1.5">Separate multiple cities with commas</p>
            </div>

            {/* Work Arrangement */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-3">
                <Settings className="w-4 h-4 inline mr-2 text-cyan-600" />
                Work Arrangement
              </label>
              <div className="grid grid-cols-3 gap-3">
                {WORK_ARRANGEMENTS.map((arrangement) => {
                  const selected = workArrangements.includes(arrangement.value);
                  return (
                    <button
                      key={arrangement.value}
                      onClick={() => toggleWorkArrangement(arrangement.value)}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        selected
                          ? 'border-cyan-600 bg-cyan-50'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <arrangement.icon
                        className={`w-6 h-6 mx-auto mb-2 ${
                          selected ? 'text-cyan-600' : 'text-slate-400'
                        }`}
                      />
                      <p
                        className={`text-sm font-medium ${
                          selected ? 'text-cyan-900' : 'text-slate-700'
                        }`}
                      >
                        {arrangement.label}
                      </p>
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-slate-500 mt-1.5">Select all that apply</p>
            </div>
          </div>

          {/* Feedback */}
          {feedback && (
            <div
              className={`mt-6 p-3 rounded-xl text-sm ${
                feedback.type === 'success'
                  ? 'bg-green-50 border border-green-200 text-green-700'
                  : 'bg-red-50 border border-red-200 text-red-700'
              }`}
            >
              {feedback.type === 'success' && <Check className="w-4 h-4 inline mr-1.5" />}
              {feedback.message}
            </div>
          )}

          {/* Save */}
          <div className="mt-6 flex justify-end">
            <button onClick={handleSave} disabled={saving} className={btnPrimary}>
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 inline mr-1.5 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Preferences'
              )}
            </button>
          </div>
        </div>
      </motion.main>
      <Footer />
    </div>
  );
}
