import { create } from 'zustand';
import { AppState, Hotel, LogEntry } from './types';
import { INITIAL_FILTERS } from './constants';
import { uuidv4 } from './utils';

export const useStore = create<AppState>((set, get) => ({
  hotels: [],
  filteredHotels: [],
  filters: INITIAL_FILTERS,
  logs: [],
  isJobRunning: false,
  jobProgress: { current: 0, total: 0, jobType: null },

  setHotels: (data: Hotel[]) => {
    set({ hotels: data, filteredHotels: data });
  },

  setFilter: (key, value) => {
    const state = get();
    const newFilters = { ...state.filters, [key]: value };
    
    // Apply filters
    let filtered = state.hotels.filter(h => {
      const matchCity = newFilters.city ? h.il === newFilters.city : true;
      const matchDistrict = newFilters.district ? h.ilce === newFilters.district : true;
      const matchType = newFilters.type ? h.tur === newFilters.type : true;
      const matchSearch = newFilters.search ? 
        (h.ad.toLowerCase().includes(newFilters.search.toLowerCase()) || 
         h.il.toLowerCase().includes(newFilters.search.toLowerCase())) : true;
      
      return matchCity && matchDistrict && matchType && matchSearch;
    });

    set({ filters: newFilters, filteredHotels: filtered });
  },

  updateHotel: (id, updates) => {
    set(state => {
      const newHotels = state.hotels.map(h => h.id === id ? { ...h, ...updates } : h);
      // Re-apply filters to keep view consistent (simplified here by just mapping filtered)
      const newFiltered = state.filteredHotels.map(h => h.id === id ? { ...h, ...updates } : h);
      return { hotels: newHotels, filteredHotels: newFiltered };
    });
  },

  addLog: (message, type, hotelId) => {
    const entry: LogEntry = {
      id: uuidv4(),
      timestamp: new Date(),
      message,
      type,
      hotelId
    };
    set(state => ({ logs: [entry, ...state.logs].slice(0, 1000) })); // Keep last 1000 logs
  },

  setJobStatus: (isRunning, type, current, total) => {
    set(state => ({
      isJobRunning: isRunning,
      jobProgress: {
        jobType: type || state.jobProgress.jobType,
        current: current !== undefined ? current : state.jobProgress.current,
        total: total !== undefined ? total : state.jobProgress.total,
      }
    }));
  },

  reset: () => {
    set({
      hotels: [],
      filteredHotels: [],
      filters: INITIAL_FILTERS,
      logs: [],
      isJobRunning: false
    });
  }
}));