import { FilterState } from './types';

export const INITIAL_FILTERS: FilterState = {
  city: '',
  district: '',
  type: '',
  search: ''
};

export const CORS_PROXY = "https://api.allorigins.win/get?url=";

// Limits for the demo to prevent browser crash / infinite loops
export const CONCURRENCY_LIMIT = 3; 
export const RETRY_LIMIT = 2;
