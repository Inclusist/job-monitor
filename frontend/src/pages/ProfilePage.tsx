import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  User as UserIcon,
  Upload,
  Trash2,
  Star,
  FileText,
  Pencil,
  Check,
  X,
  Loader2,
  Plus,
  Briefcase,
  GraduationCap,
  Languages,
  Sparkles,
  FolderOpen,
  Award,
  ClipboardCheck,
  Bot,
  AlertTriangle,
} from 'lucide-react';
import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';
import {
  getProfile,
  uploadCV,
  deleteCV,
  setPrimaryCV,
  updateProfile,
  updateContactInfo,
  saveProjects,
  deleteProfile,
} from '../services/profile';
import type { CVProfile, ClaimedData } from '../types';

const cardClass = 'border border-cyan-200 rounded-2xl p-8 bg-white shadow-sm';
const btnPrimary = 'px-4 py-2 bg-cyan-600 text-white rounded-xl font-semibold hover:bg-cyan-500 transition-colors text-sm';
const btnSecondary = 'px-4 py-2 border border-cyan-300 text-cyan-700 rounded-xl font-semibold hover:bg-cyan-50 transition-colors text-sm';

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ['profile'],
    queryFn: getProfile,
  });

  const [editingSection, setEditingSection] = useState<string | null>(null);

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

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-cyan-50">
        <Header />
        <div className="pt-28 max-w-4xl mx-auto px-6">
          <p className="text-red-600">Failed to load profile.</p>
        </div>
      </div>
    );
  }

  const { user, cvs, profile, claimed_data } = data;

  const active_cv_id = data.active_cv_id;

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-cyan-50">
      <Header />
      <motion.main
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="pt-28 pb-16 max-w-4xl mx-auto px-6 space-y-8"
      >
        <h1 className="text-3xl font-bold text-slate-900">Profile</h1>

        {/* Onboarding Banner */}
        {!user.onboarding_completed && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-gradient-to-r from-cyan-600 to-cyan-700 rounded-2xl p-6 text-white shadow-lg border border-cyan-500/30 flex flex-col md:flex-row items-center justify-between gap-4"
          >
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold">Complete your setup!</h2>
                <p className="text-cyan-50 text-sm">You haven't finished the onboarding. Complete it to get the best job matches.</p>
              </div>
            </div>
            <Link
              to="/onboarding"
              className="bg-white text-cyan-700 px-6 py-2.5 rounded-xl font-bold hover:bg-cyan-50 transition-all shadow-md flex items-center space-x-2"
            >
              <span>Resume Onboarding</span>
              <Sparkles className="w-4 h-4" />
            </Link>
          </motion.div>
        )}

        <UserInfoCard
          user={user}
          editing={editingSection === 'user'}
          onEdit={() => setEditingSection('user')}
          onCancel={() => setEditingSection(null)}
          onSaved={() => { setEditingSection(null); queryClient.invalidateQueries({ queryKey: ['profile'] }); }}
        />

        <CVManagementCard
          cvs={cvs}
          activeCvId={active_cv_id}
          onChanged={() => queryClient.invalidateQueries({ queryKey: ['profile'] })}
        />

        {profile ? (
          <>
            <ProfileSummaryCard
              profile={profile}
              editing={editingSection === 'summary'}
              onEdit={() => setEditingSection('summary')}
              onCancel={() => setEditingSection(null)}
              onSaved={() => { setEditingSection(null); queryClient.invalidateQueries({ queryKey: ['profile'] }); }}
            />

            {profile.semantic_summary && <AISummaryCard profile={profile} />}

            <SkillsCard
              profile={profile}
              editing={editingSection === 'skills'}
              onEdit={() => setEditingSection('skills')}
              onCancel={() => setEditingSection(null)}
              onSaved={() => { setEditingSection(null); queryClient.invalidateQueries({ queryKey: ['profile'] }); }}
            />

            <CompetenciesCard profile={profile} />

            <ProjectsCard
              profile={profile}
              editing={editingSection === 'projects'}
              onEdit={() => setEditingSection('projects')}
              onCancel={() => setEditingSection(null)}
              onSaved={() => { setEditingSection(null); queryClient.invalidateQueries({ queryKey: ['profile'] }); }}
            />

            <WorkExperienceCard
              profile={profile}
              editing={editingSection === 'work'}
              onEdit={() => setEditingSection('work')}
              onCancel={() => setEditingSection(null)}
              onSaved={() => { setEditingSection(null); queryClient.invalidateQueries({ queryKey: ['profile'] }); }}
            />

            <EducationCard
              profile={profile}
              editing={editingSection === 'education'}
              onEdit={() => setEditingSection('education')}
              onCancel={() => setEditingSection(null)}
              onSaved={() => { setEditingSection(null); queryClient.invalidateQueries({ queryKey: ['profile'] }); }}
            />

            <LanguagesCard
              profile={profile}
              editing={editingSection === 'languages'}
              onEdit={() => setEditingSection('languages')}
              onCancel={() => setEditingSection(null)}
              onSaved={() => { setEditingSection(null); queryClient.invalidateQueries({ queryKey: ['profile'] }); }}
            />

            {claimed_data && <ClaimedItemsCard claimedData={claimed_data} />}
          </>
        ) : (
          <div className={cardClass}>
            <p className="text-slate-500 text-center py-4">
              No profile yet — upload a CV to get started.
            </p>
          </div>
        )}

        {/* Danger Zone */}
        <DangerZoneCard />
      </motion.main>
      <Footer />
    </div>
  );
}

/* ─── User Info Card ─── */

interface UserInfoCardProps {
  user: NonNullable<ReturnType<typeof Object>>;
  editing: boolean;
  onEdit: () => void;
  onCancel: () => void;
  onSaved: () => void;
}

function UserInfoCard({ user, editing, onEdit, onCancel, onSaved }: UserInfoCardProps) {
  const [name, setName] = useState(user.name || '');
  const [location, setLocation] = useState(user.location || '');
  const [userRole, setUserRole] = useState(user.user_role || '');
  const [resumeName, setResumeName] = useState(user.resume_name || '');
  const [resumeEmail, setResumeEmail] = useState(user.resume_email || '');
  const [resumePhone, setResumePhone] = useState(user.resume_phone || '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateProfile({ user: { name, location, user_role: userRole } });
      await updateContactInfo({ resume_name: resumeName, resume_email: resumeEmail, resume_phone: resumePhone });
      onSaved();
    } finally {
      setSaving(false);
    }
  };

  const handleStartEdit = () => {
    setName(user.name || '');
    setLocation(user.location || '');
    setUserRole(user.user_role || '');
    setResumeName(user.resume_name || '');
    setResumeEmail(user.resume_email || '');
    setResumePhone(user.resume_phone || '');
    onEdit();
  };

  return (
    <div className={cardClass}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <UserIcon className="w-5 h-5 text-cyan-600" />
          <h2 className="text-xl font-semibold text-slate-900">User Info</h2>
        </div>
        {!editing ? (
          <button onClick={handleStartEdit} className={btnSecondary}>
            <Pencil className="w-4 h-4 inline mr-1" />Edit
          </button>
        ) : (
          <div className="flex space-x-2">
            <button onClick={onCancel} className={btnSecondary}><X className="w-4 h-4 inline mr-1" />Cancel</button>
            <button onClick={handleSave} disabled={saving} className={btnPrimary}>
              {saving ? <Loader2 className="w-4 h-4 inline mr-1 animate-spin" /> : <Check className="w-4 h-4 inline mr-1" />}Save
            </button>
          </div>
        )}
      </div>

      <div className="flex items-start space-x-6">
        {user.avatar_url ? (
          <img src={user.avatar_url} alt={user.name} className="w-16 h-16 rounded-full" referrerPolicy="no-referrer" />
        ) : (
          <div className="w-16 h-16 rounded-full bg-cyan-100 flex items-center justify-center text-cyan-700 text-2xl font-bold">
            {user.name?.charAt(0) || '?'}
          </div>
        )}

        <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Name" value={name} editing={editing} onChange={setName} />
          <Field label="Email" value={user.email} editing={false} />
          <Field label="Location" value={location} editing={editing} onChange={setLocation} placeholder="e.g. Berlin, Germany" />
          <Field label="Role" value={userRole} editing={editing} onChange={setUserRole} placeholder="e.g. Software Engineer" />

          <div className="md:col-span-2 border-t border-cyan-100 pt-4 mt-2">
            <p className="text-xs text-slate-400 mb-3">Resume Contact Info (used on generated resumes)</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Field label="Resume Name" value={resumeName} editing={editing} onChange={setResumeName} placeholder={user.name || ''} />
              <Field label="Resume Email" value={resumeEmail} editing={editing} onChange={setResumeEmail} placeholder={user.email || ''} />
              <Field label="Resume Phone" value={resumePhone} editing={editing} onChange={setResumePhone} placeholder="+1 (555) 123-4567" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, editing, onChange, placeholder }: {
  label: string; value: string; editing: boolean; onChange?: (v: string) => void; placeholder?: string;
}) {
  return (
    <div>
      <label className="block text-xs text-slate-500 mb-1">{label}</label>
      {editing && onChange ? (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full border border-cyan-200 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-cyan-400"
        />
      ) : (
        <p className="text-sm text-slate-900">{value || <span className="text-slate-400">Not set</span>}</p>
      )}
    </div>
  );
}

/* ─── CV Management Card ─── */

function CVManagementCard({ cvs, activeCvId, onChanged }: {
  cvs: { id: number; file_name: string; file_type: string; uploaded_date: string; is_primary: boolean }[];
  activeCvId: number | null;
  onChanged: () => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  const deleteMutation = useMutation({
    mutationFn: deleteCV,
    onSuccess: onChanged,
  });

  const setPrimaryMutation = useMutation({
    mutationFn: setPrimaryCV,
    onSuccess: onChanged,
  });

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError('');
    try {
      const result = await uploadCV(file, true);
      if (!result.success) {
        setUploadError(result.error || 'Upload failed');
      }
      onChanged();
    } catch {
      setUploadError('Upload failed. Please try again.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className={cardClass}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <FileText className="w-5 h-5 text-cyan-600" />
          <h2 className="text-xl font-semibold text-slate-900">CV Management</h2>
        </div>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={handleFileChange}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className={btnPrimary}
          >
            {uploading ? (
              <><Loader2 className="w-4 h-4 inline mr-1 animate-spin" />Analyzing...</>
            ) : (
              <><Upload className="w-4 h-4 inline mr-1" />Upload CV</>
            )}
          </button>
        </div>
      </div>

      {uploading && (
        <div className="mb-4 p-4 bg-cyan-50 border border-cyan-200 rounded-xl text-sm text-cyan-800">
          <Loader2 className="w-4 h-4 inline mr-2 animate-spin" />
          Analyzing your CV with AI... This may take up to a minute.
        </div>
      )}

      {uploadError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {uploadError}
        </div>
      )}

      {cvs.length === 0 ? (
        <p className="text-slate-500 text-sm">No CVs uploaded yet.</p>
      ) : (
        <ul className="space-y-3">
          {cvs.map((cv) => (
            <li key={cv.id} className="flex items-center justify-between p-4 bg-cyan-50/50 rounded-xl border border-cyan-100">
              <div className="flex items-center space-x-3">
                <FileText className="w-5 h-5 text-slate-400" />
                <div>
                  <p className="text-sm font-medium text-slate-900">{cv.file_name}</p>
                  <p className="text-xs text-slate-500">
                    {cv.file_type.toUpperCase()} &middot; {new Date(cv.uploaded_date).toLocaleDateString()}
                  </p>
                </div>
                {cv.is_primary && (
                  <span className="px-2 py-0.5 bg-cyan-100 text-cyan-700 text-xs rounded-full font-medium">Primary</span>
                )}
              </div>
              <div className="flex items-center space-x-2">
                {!cv.is_primary && (
                  <button
                    onClick={() => setPrimaryMutation.mutate(cv.id)}
                    className="p-2 text-slate-400 hover:text-cyan-600 transition-colors"
                    title="Set as primary"
                  >
                    <Star className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={() => { if (confirm('Delete this CV?')) deleteMutation.mutate(cv.id); }}
                  className="p-2 text-slate-400 hover:text-red-600 transition-colors"
                  title="Delete CV"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ─── Profile Summary Card ─── */

interface SectionCardProps {
  profile: CVProfile;
  editing: boolean;
  onEdit: () => void;
  onCancel: () => void;
  onSaved: () => void;
}

function ProfileSummaryCard({ profile, editing, onEdit, onCancel, onSaved }: SectionCardProps) {
  const [summary, setSummary] = useState(profile.expertise_summary || '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateProfile({ profile: { expertise_summary: summary } });
      onSaved();
    } finally {
      setSaving(false);
    }
  };

  const handleStartEdit = () => {
    setSummary(profile.expertise_summary || '');
    onEdit();
  };

  return (
    <div className={cardClass}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-5 h-5 text-cyan-600" />
          <h2 className="text-xl font-semibold text-slate-900">Profile Summary</h2>
        </div>
        <SectionEditButtons editing={editing} saving={saving} onEdit={handleStartEdit} onCancel={onCancel} onSave={handleSave} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <InfoBadge label="Career Level" value={profile.career_level} />
        <InfoBadge label="Experience" value={profile.total_years_experience ? `${profile.total_years_experience} years` : undefined} />
        <InfoBadge label="Extracted Role" value={profile.extracted_role} />
        <InfoBadge label="Seniority" value={profile.derived_seniority} />
      </div>

      {profile.domain_expertise && profile.domain_expertise.length > 0 && (
        <div className="mb-4">
          <label className="block text-xs text-slate-500 mb-2">Domain Expertise</label>
          <div className="flex flex-wrap gap-2">
            {profile.domain_expertise.map((d, i) => (
              <span key={i} className="px-3 py-1 bg-slate-100 text-slate-700 text-xs rounded-full">{d}</span>
            ))}
          </div>
        </div>
      )}

      <div>
        <label className="block text-xs text-slate-500 mb-2">Expertise Summary</label>
        {editing ? (
          <textarea
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            rows={4}
            className="w-full border border-cyan-200 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-cyan-400"
          />
        ) : (
          <p className="text-sm text-slate-700 whitespace-pre-wrap">{profile.expertise_summary || <span className="text-slate-400">Not set</span>}</p>
        )}
      </div>
    </div>
  );
}

function InfoBadge({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="p-3 bg-cyan-50 rounded-xl">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-sm font-medium text-slate-900 mt-1">{value || '—'}</p>
    </div>
  );
}

/* ─── Skills Card ─── */

function SkillsCard({ profile, editing, onEdit, onCancel, onSaved }: SectionCardProps) {
  const [techSkills, setTechSkills] = useState<string[]>(profile.technical_skills || []);
  const [softSkills, setSoftSkills] = useState<string[]>(profile.soft_skills || []);
  const [techInput, setTechInput] = useState('');
  const [softInput, setSoftInput] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateProfile({ profile: { technical_skills: techSkills, soft_skills: softSkills } });
      onSaved();
    } finally {
      setSaving(false);
    }
  };

  const handleStartEdit = () => {
    setTechSkills(profile.technical_skills || []);
    setSoftSkills(profile.soft_skills || []);
    onEdit();
  };

  const addSkill = (type: 'tech' | 'soft') => {
    const input = type === 'tech' ? techInput.trim() : softInput.trim();
    if (!input) return;
    if (type === 'tech') {
      if (!techSkills.includes(input)) setTechSkills([...techSkills, input]);
      setTechInput('');
    } else {
      if (!softSkills.includes(input)) setSoftSkills([...softSkills, input]);
      setSoftInput('');
    }
  };

  return (
    <div className={cardClass}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-5 h-5 text-cyan-600" />
          <h2 className="text-xl font-semibold text-slate-900">Skills</h2>
        </div>
        <SectionEditButtons editing={editing} saving={saving} onEdit={handleStartEdit} onCancel={onCancel} onSave={handleSave} />
      </div>

      <div className="space-y-6">
        <div>
          <label className="block text-xs text-slate-500 mb-2">Technical Skills</label>
          <div className="flex flex-wrap gap-2">
            {(editing ? techSkills : profile.technical_skills || []).map((s, i) => (
              <span key={i} className="px-3 py-1 bg-cyan-100 text-cyan-800 text-xs rounded-full font-medium flex items-center">
                {s}
                {editing && (
                  <button onClick={() => setTechSkills(techSkills.filter((_, j) => j !== i))} className="ml-1.5 text-cyan-600 hover:text-cyan-900">
                    <X className="w-3 h-3" />
                  </button>
                )}
              </span>
            ))}
          </div>
          {editing && (
            <div className="flex mt-2 space-x-2">
              <input
                value={techInput}
                onChange={(e) => setTechInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSkill('tech'))}
                placeholder="Add technical skill"
                className="flex-1 border border-cyan-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400"
              />
              <button onClick={() => addSkill('tech')} className={btnSecondary}><Plus className="w-4 h-4" /></button>
            </div>
          )}
        </div>

        <div>
          <label className="block text-xs text-slate-500 mb-2">Soft Skills</label>
          <div className="flex flex-wrap gap-2">
            {(editing ? softSkills : profile.soft_skills || []).map((s, i) => (
              <span key={i} className="px-3 py-1 bg-amber-100 text-amber-800 text-xs rounded-full font-medium flex items-center">
                {s}
                {editing && (
                  <button onClick={() => setSoftSkills(softSkills.filter((_, j) => j !== i))} className="ml-1.5 text-amber-600 hover:text-amber-900">
                    <X className="w-3 h-3" />
                  </button>
                )}
              </span>
            ))}
          </div>
          {editing && (
            <div className="flex mt-2 space-x-2">
              <input
                value={softInput}
                onChange={(e) => setSoftInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSkill('soft'))}
                placeholder="Add soft skill"
                className="flex-1 border border-cyan-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400"
              />
              <button onClick={() => addSkill('soft')} className={btnSecondary}><Plus className="w-4 h-4" /></button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Work Experience Card ─── */

type WorkEntry = CVProfile['work_experience'][number];

function WorkExperienceCard({ profile, editing, onEdit, onCancel, onSaved }: SectionCardProps) {
  const [entries, setEntries] = useState<WorkEntry[]>(profile.work_experience || []);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateProfile({ profile: { work_experience: entries } });
      onSaved();
    } finally {
      setSaving(false);
    }
  };

  const handleStartEdit = () => {
    setEntries(JSON.parse(JSON.stringify(profile.work_experience || [])));
    onEdit();
  };

  const updateEntry = (idx: number, field: keyof WorkEntry, value: string | string[]) => {
    setEntries(entries.map((e, i) => i === idx ? { ...e, [field]: value } : e));
  };

  const removeEntry = (idx: number) => setEntries(entries.filter((_, i) => i !== idx));

  const addEntry = () => setEntries([...entries, { title: '', company: '', duration: '', description: '' }]);

  const displayEntries = editing ? entries : (profile.work_experience || []);

  return (
    <div className={cardClass}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Briefcase className="w-5 h-5 text-cyan-600" />
          <h2 className="text-xl font-semibold text-slate-900">Work Experience</h2>
        </div>
        <SectionEditButtons editing={editing} saving={saving} onEdit={handleStartEdit} onCancel={onCancel} onSave={handleSave} />
      </div>

      {displayEntries.length === 0 ? (
        <p className="text-slate-400 text-sm">No work experience entries.</p>
      ) : (
        <div className="space-y-4">
          {displayEntries.map((entry, idx) => (
            <div key={idx} className="p-4 bg-cyan-50/50 rounded-xl border border-cyan-100">
              {editing ? (
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-3">
                      <input value={entry.title} onChange={(e) => updateEntry(idx, 'title', e.target.value)} placeholder="Title" className="border border-cyan-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400" />
                      <input value={entry.company} onChange={(e) => updateEntry(idx, 'company', e.target.value)} placeholder="Company" className="border border-cyan-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400" />
                      <input value={entry.duration || ''} onChange={(e) => updateEntry(idx, 'duration', e.target.value)} placeholder="Duration" className="border border-cyan-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400" />
                    </div>
                    <button onClick={() => removeEntry(idx)} className="ml-2 p-1 text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                  </div>
                  <textarea value={entry.description || ''} onChange={(e) => updateEntry(idx, 'description', e.target.value)} placeholder="Description" rows={2} className="w-full border border-cyan-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400" />
                </div>
              ) : (
                <>
                  <div className="flex items-baseline justify-between">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{entry.title}</p>
                      <p className="text-sm text-slate-600">{entry.company}</p>
                    </div>
                    {entry.duration && <span className="text-xs text-slate-500">{entry.duration}</span>}
                  </div>
                  {entry.description && !(entry.key_achievements && entry.key_achievements.length > 0 && entry.description.length > 200) && (
                    <p className="text-sm text-slate-600 mt-2">{entry.description}</p>
                  )}
                  {entry.key_achievements && entry.key_achievements.length > 0 && (
                    <ul className="mt-2 list-disc list-inside text-sm text-slate-600">
                      {entry.key_achievements.map((a, i) => <li key={i}>{a}</li>)}
                    </ul>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {editing && (
        <button onClick={addEntry} className={`mt-4 ${btnSecondary}`}>
          <Plus className="w-4 h-4 inline mr-1" />Add Entry
        </button>
      )}
    </div>
  );
}

/* ─── Education Card ─── */

type EduEntry = CVProfile['education'][number];

function EducationCard({ profile, editing, onEdit, onCancel, onSaved }: SectionCardProps) {
  const [entries, setEntries] = useState<EduEntry[]>(profile.education || []);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateProfile({ profile: { education: entries } });
      onSaved();
    } finally {
      setSaving(false);
    }
  };

  const handleStartEdit = () => {
    setEntries(JSON.parse(JSON.stringify(profile.education || [])));
    onEdit();
  };

  const updateEntry = (idx: number, field: keyof EduEntry, value: string) => {
    setEntries(entries.map((e, i) => i === idx ? { ...e, [field]: value } : e));
  };

  const removeEntry = (idx: number) => setEntries(entries.filter((_, i) => i !== idx));
  const addEntry = () => setEntries([...entries, { degree: '', institution: '', year: '' }]);

  const displayEntries = editing ? entries : (profile.education || []);

  return (
    <div className={cardClass}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <GraduationCap className="w-5 h-5 text-cyan-600" />
          <h2 className="text-xl font-semibold text-slate-900">Education</h2>
        </div>
        <SectionEditButtons editing={editing} saving={saving} onEdit={handleStartEdit} onCancel={onCancel} onSave={handleSave} />
      </div>

      {displayEntries.length === 0 ? (
        <p className="text-slate-400 text-sm">No education entries.</p>
      ) : (
        <div className="space-y-3">
          {displayEntries.map((entry, idx) => (
            <div key={idx} className="p-4 bg-cyan-50/50 rounded-xl border border-cyan-100">
              {editing ? (
                <div className="flex items-center space-x-3">
                  <input value={entry.degree} onChange={(e) => updateEntry(idx, 'degree', e.target.value)} placeholder="Degree" className="flex-1 border border-cyan-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400" />
                  <input value={entry.institution} onChange={(e) => updateEntry(idx, 'institution', e.target.value)} placeholder="Institution" className="flex-1 border border-cyan-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400" />
                  <input value={entry.year || ''} onChange={(e) => updateEntry(idx, 'year', e.target.value)} placeholder="Year" className="w-24 border border-cyan-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400" />
                  <button onClick={() => removeEntry(idx)} className="p-1 text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                </div>
              ) : (
                <div className="flex items-baseline justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{entry.degree}</p>
                    <p className="text-sm text-slate-600">{entry.institution}</p>
                  </div>
                  {entry.year && <span className="text-xs text-slate-500">{entry.year}</span>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {editing && (
        <button onClick={addEntry} className={`mt-4 ${btnSecondary}`}>
          <Plus className="w-4 h-4 inline mr-1" />Add Entry
        </button>
      )}
    </div>
  );
}

/* ─── Languages Card ─── */

function LanguagesCard({ profile, editing, onEdit, onCancel, onSaved }: SectionCardProps) {
  const normalize = (langs: CVProfile['languages']): { language: string; level: string }[] =>
    (langs || []).map((l) => typeof l === 'string' ? { language: l, level: '' } : { language: l.language, level: l.level || '' });

  const [entries, setEntries] = useState(normalize(profile.languages));
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateProfile({ profile: { languages: entries } });
      onSaved();
    } finally {
      setSaving(false);
    }
  };

  const handleStartEdit = () => {
    setEntries(normalize(profile.languages));
    onEdit();
  };

  const updateEntry = (idx: number, field: 'language' | 'level', value: string) => {
    setEntries(entries.map((e, i) => i === idx ? { ...e, [field]: value } : e));
  };

  const removeEntry = (idx: number) => setEntries(entries.filter((_, i) => i !== idx));
  const addEntry = () => setEntries([...entries, { language: '', level: '' }]);

  const displayEntries = editing ? entries : normalize(profile.languages);

  return (
    <div className={cardClass}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Languages className="w-5 h-5 text-cyan-600" />
          <h2 className="text-xl font-semibold text-slate-900">Languages</h2>
        </div>
        <SectionEditButtons editing={editing} saving={saving} onEdit={handleStartEdit} onCancel={onCancel} onSave={handleSave} />
      </div>

      {displayEntries.length === 0 ? (
        <p className="text-slate-400 text-sm">No languages listed.</p>
      ) : (
        <div className="space-y-3">
          {displayEntries.map((entry, idx) => (
            <div key={idx} className="p-4 bg-cyan-50/50 rounded-xl border border-cyan-100">
              {editing ? (
                <div className="flex items-center space-x-3">
                  <input value={entry.language} onChange={(e) => updateEntry(idx, 'language', e.target.value)} placeholder="Language" className="flex-1 border border-cyan-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400" />
                  <input value={entry.level} onChange={(e) => updateEntry(idx, 'level', e.target.value)} placeholder="Level (e.g. Native, B2)" className="flex-1 border border-cyan-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400" />
                  <button onClick={() => removeEntry(idx)} className="p-1 text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                </div>
              ) : (
                <div className="flex items-baseline justify-between">
                  <p className="text-sm font-medium text-slate-900">{entry.language}</p>
                  {entry.level && <span className="text-xs text-slate-500">{entry.level}</span>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {editing && (
        <button onClick={addEntry} className={`mt-4 ${btnSecondary}`}>
          <Plus className="w-4 h-4 inline mr-1" />Add Entry
        </button>
      )}
    </div>
  );
}

/* ─── AI Summary Card ─── */

function AISummaryCard({ profile }: { profile: CVProfile }) {
  return (
    <div className={`${cardClass} border-l-4 border-l-indigo-400`}>
      <div className="flex items-center space-x-2 mb-4">
        <Bot className="w-5 h-5 text-indigo-500" />
        <h2 className="text-xl font-semibold text-slate-900">AI Profile Summary</h2>
      </div>
      <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
        {profile.semantic_summary}
      </p>
    </div>
  );
}

/* ─── Competencies Card ─── */

function CompetenciesCard({ profile }: { profile: CVProfile }) {
  const competencies = profile.competencies || [];
  if (competencies.length === 0) return null;

  return (
    <div className={`${cardClass} border-l-4 border-l-green-400`}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Award className="w-5 h-5 text-green-600" />
          <h2 className="text-xl font-semibold text-slate-900">Core Competencies</h2>
        </div>
        <span className="px-2.5 py-1 bg-green-100 text-green-700 text-xs rounded-full font-medium">
          {competencies.length} competencies
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {competencies.map((comp, i) => {
          const name = typeof comp === 'string' ? comp : comp.name;
          const evidence = typeof comp === 'string' ? undefined : comp.evidence;
          return (
            <div key={i} className="p-4 bg-green-50/50 rounded-xl border border-green-100">
              <p className="text-sm font-semibold text-green-800">{name}</p>
              {evidence && <p className="text-xs text-slate-600 mt-1">{evidence}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Projects Card ─── */

function ProjectsCard({ profile, editing, onEdit, onCancel, onSaved }: SectionCardProps) {
  const [entries, setEntries] = useState<string[]>(profile.projects || []);
  const [saving, setSaving] = useState(false);
  const [newProject, setNewProject] = useState('');

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveProjects(entries);
      onSaved();
    } finally {
      setSaving(false);
    }
  };

  const handleStartEdit = () => {
    setEntries([...(profile.projects || [])]);
    setNewProject('');
    onEdit();
  };

  const removeEntry = (idx: number) => setEntries(entries.filter((_, i) => i !== idx));

  const addEntry = () => {
    const text = newProject.trim();
    if (!text) return;
    setEntries([...entries, text]);
    setNewProject('');
  };

  const displayEntries = editing ? entries : (profile.projects || []);

  return (
    <div className={cardClass}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <FolderOpen className="w-5 h-5 text-cyan-600" />
          <h2 className="text-xl font-semibold text-slate-900">Projects</h2>
        </div>
        <SectionEditButtons editing={editing} saving={saving} onEdit={handleStartEdit} onCancel={onCancel} onSave={handleSave} />
      </div>

      {displayEntries.length === 0 && !editing ? (
        <p className="text-slate-400 text-sm">No projects yet. Add your personal projects and portfolio work.</p>
      ) : (
        <div className="space-y-3">
          {displayEntries.map((project, idx) => (
            <div key={idx} className="p-4 bg-cyan-50/50 rounded-xl border border-cyan-100">
              {editing ? (
                <div className="flex items-start space-x-2">
                  <textarea
                    value={project}
                    onChange={(e) => setEntries(entries.map((p, i) => i === idx ? e.target.value : p))}
                    rows={3}
                    className="flex-1 border border-cyan-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400"
                  />
                  <button onClick={() => removeEntry(idx)} className="p-1 text-red-400 hover:text-red-600 mt-1">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <p className="text-sm text-slate-700 whitespace-pre-wrap">{project}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {editing && (
        <div className="mt-4 space-y-2">
          <textarea
            value={newProject}
            onChange={(e) => setNewProject(e.target.value)}
            rows={3}
            placeholder="Describe your project..."
            className="w-full border border-cyan-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400"
          />
          <button onClick={addEntry} className={btnSecondary}>
            <Plus className="w-4 h-4 inline mr-1" />Add Project
          </button>
        </div>
      )}
    </div>
  );
}

/* ─── Claimed Items Card (read-only) ─── */

function ClaimedItemsCard({ claimedData }: { claimedData: ClaimedData }) {
  const compEntries = Object.entries(claimedData.competencies || {});
  const skillEntries = Object.entries(claimedData.skills || {});
  const total = compEntries.length + skillEntries.length;

  if (total === 0) return null;

  return (
    <div className={`${cardClass} border-l-4 border-l-indigo-400`}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <ClipboardCheck className="w-5 h-5 text-indigo-600" />
          <h2 className="text-xl font-semibold text-slate-900">Claimed Items for Resume</h2>
        </div>
        <span className="px-2.5 py-1 bg-indigo-100 text-indigo-700 text-xs rounded-full font-medium">
          {total} items
        </span>
      </div>

      <p className="text-xs text-slate-500 mb-4">
        Competencies and skills you've claimed with evidence. These are automatically included in your generated resumes.
      </p>

      {compEntries.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-indigo-700 mb-3">Claimed Competencies ({compEntries.length})</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {compEntries.map(([name, details]) => (
              <div key={name} className="p-3 bg-indigo-50/50 rounded-xl border-l-4 border-l-indigo-300">
                <p className="text-sm font-medium text-slate-900">{name}</p>
                {details.evidence && <p className="text-xs text-slate-600 mt-1">{details.evidence}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {skillEntries.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-blue-700 mb-3">Claimed Skills ({skillEntries.length})</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {skillEntries.map(([name, details]) => (
              <div key={name} className="p-3 bg-blue-50/50 rounded-xl border-l-4 border-l-blue-300">
                <p className="text-sm font-medium text-slate-900">{name}</p>
                {details.evidence && <p className="text-xs text-slate-600 mt-1">{details.evidence}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Shared Edit Buttons ─── */

function SectionEditButtons({ editing, saving, onEdit, onCancel, onSave }: {
  editing: boolean; saving: boolean; onEdit: () => void; onCancel: () => void; onSave: () => void;
}) {
  if (!editing) {
    return (
      <button onClick={onEdit} className={btnSecondary}>
        <Pencil className="w-4 h-4 inline mr-1" />Edit
      </button>
    );
  }
  return (
    <div className="flex space-x-2">
      <button onClick={onCancel} className={btnSecondary}><X className="w-4 h-4 inline mr-1" />Cancel</button>
      <button onClick={onSave} disabled={saving} className={btnPrimary}>
        {saving ? <Loader2 className="w-4 h-4 inline mr-1 animate-spin" /> : <Check className="w-4 h-4 inline mr-1" />}Save
      </button>
    </div>
  );
}

/* ─── Danger Zone Card ─── */

function DangerZoneCard() {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [confirmText, setConfirmText] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');

  const handleDelete = async () => {
    if (confirmText !== 'DELETE MY ACCOUNT') {
      setError('Please type "DELETE MY ACCOUNT" exactly to confirm');
      return;
    }

    setDeleting(true);
    setError('');

    try {
      const result = await deleteProfile(confirmText);

      if (result.success) {
        // Redirect to homepage after successful deletion
        window.location.href = '/';
      } else {
        setError(result.error || 'Failed to delete account');
        setDeleting(false);
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
      setDeleting(false);
    }
  };

  return (
    <>
      <div className="border-2 border-red-200 rounded-2xl p-8 bg-red-50/30">
        <div className="flex items-center space-x-2 mb-4">
          <AlertTriangle className="w-5 h-5 text-red-600" />
          <h2 className="text-xl font-semibold text-red-900">Danger Zone</h2>
        </div>

        <p className="text-sm text-slate-600 mb-4">
          Permanently delete your account and all associated data. This action cannot be undone.
        </p>

        <button
          onClick={() => setShowConfirmDialog(true)}
          className="px-4 py-2 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700 transition-colors text-sm"
        >
          Delete My Account
        </button>
      </div>

      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl">
            <div className="flex items-center space-x-2 mb-4">
              <AlertTriangle className="w-6 h-6 text-red-600" />
              <h3 className="text-xl font-bold text-slate-900">Delete Account?</h3>
            </div>

            <div className="mb-6 space-y-3">
              <p className="text-sm text-slate-700">
                This will permanently delete:
              </p>
              <ul className="text-sm text-slate-600 list-disc list-inside space-y-1">
                <li>Your account and profile</li>
                <li>All uploaded CVs</li>
                <li>Job matches and applications</li>
                <li>Search history and preferences</li>
              </ul>
              <p className="text-sm font-semibold text-red-600">
                This action cannot be undone!
              </p>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Type <span className="font-mono bg-slate-100 px-1 rounded">DELETE MY ACCOUNT</span> to confirm:
              </label>
              <input
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="DELETE MY ACCOUNT"
                className="w-full border-2 border-red-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
                disabled={deleting}
              />
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error}
              </div>
            )}

            <div className="flex space-x-3">
              <button
                onClick={() => {
                  setShowConfirmDialog(false);
                  setConfirmText('');
                  setError('');
                }}
                disabled={deleting}
                className="flex-1 px-4 py-2 border-2 border-slate-300 text-slate-700 rounded-xl font-semibold hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting || confirmText !== 'DELETE MY ACCOUNT'}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deleting ? (
                  <>
                    <Loader2 className="w-4 h-4 inline mr-2 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  'Delete Forever'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
