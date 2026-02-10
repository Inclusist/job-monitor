export interface User {
  id: number;
  email: string;
  name: string;
  provider: 'google' | 'linkedin' | 'email';
  avatar_url?: string;
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
  priority?: 'high' | 'medium' | 'low';
  status?: 'new' | 'reviewed' | 'shortlisted' | 'applying' | 'applied' | 'interviewing' | 'offered' | 'rejected' | 'deleted';
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
  status: 'idle' | 'running';
  progress: number;
  message: string;
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

export type DashboardStatus = 'shortlisted' | 'applying' | 'applied' | 'interviewing' | 'offered' | 'rejected';

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
}

export interface DashboardResponse {
  jobs: DashboardJob[];
  count: number;
}
