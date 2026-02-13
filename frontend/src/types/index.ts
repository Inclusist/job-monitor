export interface User {
  id: number;
  email: string;
  name: string;
  provider: 'google' | 'linkedin' | 'email';
  avatar_url?: string;
  onboarding_completed?: boolean;
  onboarding_step?: number;
  onboarding_skipped?: boolean;
}

export interface UserStats {
  total_cvs: number;
  primary_cv_name?: string;
  total_jobs: number;
  high_priority: number;
}

export interface Job {
  id?: number;
  job_id?: string;
  job_table_id?: number;
  title: string;
  company?: string;
  location?: string;
  job_location?: string;
  url?: string;
  source?: string;
  posted_date?: string;
  discovered_date?: string;
  created_date?: string;
  match_score?: number;
  claude_score?: number;
  semantic_score?: number;
  ai_experience_level?: string;
  ai_work_arrangement?: string;
  ai_employment_type?: string;
  priority?: 'high' | 'medium' | 'low';
  status?: 'new' | 'viewed' | 'shortlisted' | 'applied' | 'interviewing' | 'offered' | 'rejected' | 'deleted';
  match_reasoning?: string;
  key_alignments?: string[];
  potential_gaps?: string[];
}

export interface JobsFilters {
  priority: string;
  status: string;
  min_score: number;
}

export interface JobsResponse {
  new_jobs: Job[];
  previous_jobs: Job[];
  total: number;
  filters: JobsFilters;
  has_cv: boolean;
  last_run_date?: string | null;
  error?: string;
}

export interface SearchResult {
  job_id: number;
  title: string;
  company?: string;
  location?: string;
  url?: string;
  discovered_date?: string;
  similarity: number;
  match_score: number;
}

export interface MatchingStatus {
  status: 'idle' | 'running' | 'completed' | 'error';
  stage?: string;
  progress: number;
  message: string;
  matches_found?: number;
  jobs_analyzed?: number;
  total_jobs?: number;
  current_chunk?: number;
  total_chunks?: number;
  chunks_completed?: number;
  news_snippets?: string[];
}

export interface AuthState {
  user: User | null;
  stats: UserStats | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface ResumeGenerateRequest {
  selections?: { name: string; type: 'competency' | 'skill'; evidence?: string; work_experience_ids?: number[] }[];
  instructions?: string;
  language: 'english' | 'german';
}

export interface CoverLetterGenerateRequest {
  language: 'english' | 'german';
  style: string;
  instructions?: string;
}

export interface CoverLetterStyle {
  key: string;
  name: string;
  description: string;
  best_for: string;
}

export interface DocumentCard {
  job_id: number;
  job_title: string;
  job_company: string;
  latest_date: string;
  resume?: { id: number; created_at: string; pdf_exists: boolean };
  cover_letter?: { id: number; created_at: string; pdf_exists: boolean };
}

export interface CompetencyMapping {
  job_requirement: string;
  user_strength: string;
  match_confidence: number;
  explanation: string;
}

export interface SkillMapping {
  job_skill: string;
  user_skill: string;
  match_confidence: number;
  explanation: string;
}

export interface JobDetail {
  id: number;
  title: string;
  company?: string;
  location?: string;
  description?: string;
  url?: string;
  source?: string;
  salary?: string;
  posted_date?: string;
  discovered_date?: string;
  // AI-extracted
  ai_competencies: string[];
  ai_key_skills: string[];
  ai_experience_level?: string;
  ai_work_arrangement?: string;
  ai_employment_type?: string;
  ai_core_responsibilities?: string;
  ai_requirements_summary?: string;
  // Match data
  match_score?: number;
  claude_score?: number;
  semantic_score?: number;
  priority?: string;
  status?: string;
  match_reasoning?: string;
  key_alignments: string[];
  potential_gaps: string[];
  // Structured mappings
  competency_mappings: CompetencyMapping[];
  skill_mappings: SkillMapping[];
  // Computed match maps
  competency_match_map: Record<string, boolean>;
  skill_match_map: Record<string, boolean>;
  claimed_competency_names: string[];
  claimed_skill_names: string[];
}

export type DashboardStatus = 'shortlisted' | 'applied' | 'interviewing' | 'offered' | 'rejected';

export interface DashboardJob {
  id: number;
  title: string;
  company?: string;
  location?: string;
  url?: string;
  posted_date?: string;
  discovered_date?: string;
  match_score?: number;
  priority?: string;
  status: DashboardStatus;
  match_reasoning?: string;
  key_alignments: string[];
  potential_gaps: string[];
  resume_id?: number | null;
  cover_letter_id?: number | null;
  dashboard_date?: string;
}

export interface DashboardResponse {
  jobs: DashboardJob[];
  count: number;
  status_counts?: Record<string, number>;
}

export interface CV {
  id: number;
  file_name: string;
  file_type: string;
  uploaded_date: string;
  is_primary: boolean;
}

export interface CVProfile {
  technical_skills: string[];
  soft_skills: string[];
  competencies: Array<{ name: string; evidence?: string } | string>;
  languages: Array<{ language: string; level?: string } | string>;
  education: Array<{ degree: string; institution: string; year?: string }>;
  work_experience: Array<{
    title: string;
    company: string;
    duration?: string;
    description?: string;
    key_achievements?: string[];
  }>;
  career_highlights: string[];
  projects: string[];
  expertise_summary?: string;
  career_level?: string;
  total_years_experience?: number;
  preferred_roles: string[];
  industries: string[];
  extracted_role?: string;
  derived_seniority?: string;
  domain_expertise?: string[];
  semantic_summary?: string;
  // Job preferences from CV
  desired_job_titles?: string[];
  preferred_work_locations?: string[];
  current_location?: string;
  work_arrangement_preference?: string;
}

export interface ClaimedItem {
  evidence?: string;
  work_experience_ids?: number[];
}

export interface ClaimedData {
  competencies: Record<string, ClaimedItem>;
  skills: Record<string, ClaimedItem>;
}

export interface ProfileUser {
  id: number;
  email: string;
  name: string;
  location?: string;
  user_role?: string;
  provider: string;
  avatar_url?: string;
  resume_name?: string;
  resume_email?: string;
  resume_phone?: string;
  onboarding_completed?: boolean;
  onboarding_step?: number;
  onboarding_skipped?: boolean;
}

export interface ProfileResponse {
  user: ProfileUser;
  cvs: CV[];
  profile: CVProfile | null;
  active_cv_id: number | null;
  claimed_data: ClaimedData | null;
}

export interface LearningInsights {
  success: boolean;
  ai_instructions: string;
  preferences: {
    has_feedback: boolean;
    total_feedback: number;
    agreement_rate: number;
    liked_job_examples: any[];
    disliked_job_examples: any[];
    key_preferences: {
      valued_aspects: string[];
      dealbreakers: string[];
    };
    scoring_calibration: {
      avg_original_score: number;
      avg_user_score: number;
      score_bias: number;
      needs_calibration: boolean;
    };
  };
  feedback_history: any[];
}
