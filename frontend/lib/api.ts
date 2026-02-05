import axios from 'axios';

const API = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 15000, // 15 second timeout
});

export interface Facility {
  id: string;
  name: string;
  sehir?: string;
  ilce?: string;
  type?: string;
  
  website?: string;
  website_score?: number;
  website_status: string;
  email?: string;
  email_status: string;
  
  [key: string]: any;
}

export interface JobLog {
  timestamp: string;
  level: string;
  message: string;
}

export interface NotFoundReason {
  reason: string;
  count: number;
}

export interface Job {
  job_id: string;
  status: string;
  total: number;
  done: number;
  errors: number;
  websites_found?: number;
  websites_not_found?: number;
  success_rate?: number;
  created_at?: string | null;
  finished_at?: string | null;
  elapsed_seconds?: number;
  estimated_remaining_seconds?: number;
  logs: JobLog[];
  not_found_reasons?: NotFoundReason[];
  current_action?: string | null;
  current_item?: string | null;
  last_success?: string | null;
  last_warning?: string | null;
}

export interface JobSummary {
  job_id: string;
  job_type: string;
  status: string;
  total: number;
  done: number;
  errors: number;
  websites_found: number;
  websites_not_found: number;
  success_rate: number;
  created_at: string | null;
  finished_at: string | null;
  elapsed_seconds: number;
}

export interface JobSettings {
    provider?: string;
    rate_limit?: number;
    max_concurrency?: number;
}

export const uploadFile = async (file: File, reset: boolean) => {
  const formData = new FormData();
  formData.append('file', file);
  return API.post(`/upload?reset_db=${reset}`, formData);
};

export const getFacilities = async (page: number, filters: any) => {
  return API.get('/facilities', { params: { page, ...filters } });
};

export const getFacilitiesStats = async () => {
  return API.get('/facilities/stats');
};

export const getDocumentTypes = async () => {
  return API.get('/filters/types');
};

export const startDiscovery = async (uids: string[], mode: 'all' | 'selected' = 'all') => {
  return API.post('/jobs/website-discovery', { 
      mode, 
      uids, 
      settings: { provider: 'ddg', rate_limit: 1.0, max_concurrency: 1 } 
  });
};

export const startEmailCrawl = async (uids: string[], mode: 'all' | 'selected' = 'all') => {
  return API.post('/jobs/email-crawl', { 
      mode, 
      uids, 
      settings: { rate_limit: 1.0 } 
  });
};

export const getJob = async (id: string) => {
  const res = await API.get<Job>(`/jobs/${id}`);
  return res.data;
};

export const listJobs = async () => {
  const res = await API.get<{ jobs: JobSummary[] }>(`/jobs`);
  return res.data;
};

export const cancelJob = async (jobId: string) => {
  const res = await API.delete<{ success: boolean; job_id: string; status: string; message: string }>(`/jobs/${jobId}`);
  return res.data;
};
