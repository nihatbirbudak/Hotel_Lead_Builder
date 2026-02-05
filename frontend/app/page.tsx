'use client';
import React, { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { UploadSection } from '../components/UploadSection';
import { HotelTable } from '../components/HotelTable';
import { JobControl } from '../components/JobControl';
import { LogPanel } from '../components/LogPanel';
import { Building2 } from 'lucide-react';
import Link from 'next/link';
import { getFacilities, getFacilitiesStats } from '../lib/api';

type TabType = 'pending' | 'not_found' | 'has_website' | 'has_email';

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabType>('pending');
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ city: '', search: '', type: undefined });
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  
  // Get stats for tab badges
  const { data: statsData, refetch: refetchStats } = useQuery({
    queryKey: ['facilitiesStats'],
    queryFn: () => getFacilitiesStats().then(r => r.data),
    refetchInterval: activeJobId ? 2000 : 0
  });

  // Handle tab change
  const handleTabChange = useCallback((tab: TabType) => {
    if (tab !== activeTab) {
      setActiveTab(tab);
      setPage(1);
      setSelectedIds([]); // Clear selections when changing tabs
    }
  }, [activeTab]);
  
  // Wrap setFilters to clear selections when filter changes
  const handleSetFilters = useCallback((newFilters: any) => {
    const filtersChanged = 
      newFilters.search !== filters.search || 
      newFilters.city !== filters.city || 
      newFilters.type !== filters.type;
    
    if (filtersChanged && selectedIds.length > 0) {
      // Clear selections when filter changes
      setSelectedIds([]);
    }
    setFilters(newFilters);
    // Reset to page 1 when filter changes
    if (filtersChanged) {
      setPage(1);
    }
  }, [filters, selectedIds.length]);

  // Wrap setPage to optionally clear selections on page change
  const handleSetPage = useCallback((newPage: number) => {
    // Keep selections when changing pages (they persist across pages)
    setPage(newPage);
  }, []);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['facilities', page, filters, activeTab],
    queryFn: () => getFacilities(page, { ...filters, status_filter: activeTab }).then(r => r.data),
    refetchInterval: activeJobId ? 2000 : 0
  });

  // Combined refetch
  const handleRefetch = useCallback(() => {
    refetch();
    refetchStats();
  }, [refetch, refetchStats]);

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-brand-600 rounded-lg flex items-center justify-center shadow-lg shadow-brand-500/30">
              <Building2 className="text-white w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 leading-tight">Hotel Lead Builder</h1>
              <p className="text-xs text-slate-500 font-medium">Next.js + FastAPI Monorepo</p>
            </div>
          </div>
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/jobs" className="text-slate-600 hover:text-brand-600">
              Is Gecmisi
            </Link>
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <div className="lg:col-span-3 space-y-6">
            <UploadSection onUploadSuccess={() => handleRefetch()} />
            
            {/* Tab Navigation */}
            <div className="flex border-b border-slate-200 bg-white rounded-t-xl">
              <button
                onClick={() => handleTabChange('pending')}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors relative ${
                  activeTab === 'pending' 
                    ? 'text-slate-700 border-b-2 border-slate-500 bg-slate-50/50' 
                    : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <span className="flex items-center justify-center gap-2">
                  ⏳ Aranacak
                  {statsData && (
                    <span className={`px-2 py-0.5 rounded-full text-xs ${
                      activeTab === 'pending' ? 'bg-slate-200 text-slate-700' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {statsData.pending}
                    </span>
                  )}
                </span>
              </button>
              <button
                onClick={() => handleTabChange('not_found')}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors relative ${
                  activeTab === 'not_found' 
                    ? 'text-orange-600 border-b-2 border-orange-500 bg-orange-50/50' 
                    : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <span className="flex items-center justify-center gap-2">
                  ❌ Bulunamadı
                  {statsData && (
                    <span className={`px-2 py-0.5 rounded-full text-xs ${
                      activeTab === 'not_found' ? 'bg-orange-100 text-orange-700' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {statsData.not_found}
                    </span>
                  )}
                </span>
              </button>
              <button
                onClick={() => handleTabChange('has_website')}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors relative ${
                  activeTab === 'has_website' 
                    ? 'text-blue-600 border-b-2 border-blue-500 bg-blue-50/50' 
                    : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <span className="flex items-center justify-center gap-2">
                  🌐 Website Var
                  {statsData && (
                    <span className={`px-2 py-0.5 rounded-full text-xs ${
                      activeTab === 'has_website' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {statsData.has_website}
                    </span>
                  )}
                </span>
              </button>
              <button
                onClick={() => handleTabChange('has_email')}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors relative ${
                  activeTab === 'has_email' 
                    ? 'text-green-600 border-b-2 border-green-500 bg-green-50/50' 
                    : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <span className="flex items-center justify-center gap-2">
                  ✉️ Email Var
                  {statsData && (
                    <span className={`px-2 py-0.5 rounded-full text-xs ${
                      activeTab === 'has_email' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {statsData.has_email}
                    </span>
                  )}
                </span>
              </button>
            </div>
            
            <HotelTable 
              data={data?.data || []} 
              total={data?.total || 0}
              page={page}
              setPage={handleSetPage}
              filters={filters}
              setFilters={handleSetFilters}
              isLoading={isLoading}
              selectedIds={selectedIds}
              setSelectedIds={setSelectedIds}
              activeTab={activeTab}
            />
            <LogPanel activeJobId={activeJobId} />
          </div>
          <div className="lg:col-span-1">
            <JobControl 
                activeJobId={activeJobId} 
                setActiveJobId={setActiveJobId}
                selectedIds={selectedIds}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
