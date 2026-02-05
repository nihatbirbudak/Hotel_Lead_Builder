export interface Hotel {
  id: string; // generated uuid
  rawId?: string | number;
  ad: string; // Tesis Adı
  il: string;
  ilce: string;
  sinif?: string;
  tur?: string;
  adres?: string;
  
  // Enriched Data
  website?: string;
  websiteSource?: 'duckduckgo' | 'gemini' | 'manual';
  email?: string;
  emailSource?: 'scrape' | 'gemini' | 'manual';
  
  status: 'idle' | 'searching_web' | 'web_found' | 'web_failed' | 'scanning_email' | 'email_found' | 'email_failed' | 'completed';
  lastLog?: string;
}

export type JobType = 'discovery' | 'email_harvest';

export interface LogEntry {
  id: string;
  timestamp: Date;
  hotelId?: string;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
}

export interface FilterState {
  city: string;
  district: string;
  type: string;
  search: string;
}

export interface AppState {
  hotels: Hotel[];
  filteredHotels: Hotel[];
  filters: FilterState;
  logs: LogEntry[];
  isJobRunning: boolean;
  jobProgress: {
    current: number;
    total: number;
    jobType: JobType | null;
  };
  
  // Actions
  setHotels: (data: any[]) => void;
  setFilter: (key: keyof FilterState, value: string) => void;
  updateHotel: (id: string, updates: Partial<Hotel>) => void;
  addLog: (message: string, type: LogEntry['type'], hotelId?: string) => void;
  setJobStatus: (isRunning: boolean, type?: JobType, current?: number, total?: number) => void;
  reset: () => void;
}
