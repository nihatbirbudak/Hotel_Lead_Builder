import React from 'react';
import { startDiscovery, startEmailCrawl, getJob } from '../lib/api';
import { Play, Activity, Download, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import JobProgress from './JobProgress';

interface Props {
    activeJobId: string | null;
    setActiveJobId: (id: string | null) => void;
    selectedIds: string[];
}

export const JobControl: React.FC<Props> = ({ activeJobId, setActiveJobId, selectedIds }) => {
  // Poll active job status
  const { data: job } = useQuery({
    queryKey: ['job', activeJobId],
    queryFn: () => getJob(activeJobId!),
    enabled: !!activeJobId,
    refetchInterval: 1500,
  });

  const handleStartDiscovery = async () => {
    try {
      setActiveJobId(null);
      const mode = selectedIds.length > 0 ? 'selected' : 'all';
      if (mode === 'all') {
          if (!confirm("Tüm liste taranacak. Emin misiniz?")) return;
      }
      const res = await startDiscovery(selectedIds, mode);
      setActiveJobId(res.data.job_id);
    } catch (e) {
      alert("İşlem başlatılamadı.");
    }
  };

  const handleStartEmail = async () => {
    try {
      setActiveJobId(null);
      const mode = selectedIds.length > 0 ? 'selected' : 'all';
      if (mode === 'all') {
          if (!confirm("Website bulunan tüm tesisler taranacak. Emin misiniz?")) return;
      }
      const res = await startEmailCrawl(selectedIds, mode);
      setActiveJobId(res.data.job_id);
    } catch (e) {
      alert("İşlem başlatılamadı.");
    }
  };

  const isRunning = job?.status === 'running' || job?.status === 'queued';
  const progress = job ? (job.done / (job.total || 1)) * 100 : 0;

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 sticky top-24">
      <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
        <Activity className="w-5 h-5 text-brand-500" />
        Operasyonlar
      </h3>

      <div className="space-y-3">
        <button 
          onClick={handleStartDiscovery}
          disabled={isRunning}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-lg font-medium bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 transition-all"
        >
           {isRunning && (job?.status === 'running' || job?.status === 'queued') ? <Loader2 className="w-4 h-4 animate-spin"/> : <Play className="w-4 h-4" />}
           {selectedIds.length > 0 ? `Seçilenleri Tara (${selectedIds.length})` : 'Website Keşfi (DDG)'}
        </button>

        <button 
          onClick={handleStartEmail}
          disabled={isRunning}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-lg font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-all"
        >
          {isRunning && (job?.status === 'running' || job?.status === 'queued') ? <Loader2 className="w-4 h-4 animate-spin"/> : <Play className="w-4 h-4" />}
          {selectedIds.length > 0 ? `Seçilenlerden Email Bul (${selectedIds.length})` : 'Email Topla'}
        </button>

        <div className="grid grid-cols-2 gap-2 pt-4 border-t">
            <a href="http://localhost:8000/api/export/csv" className="flex items-center justify-center gap-2 py-2 px-4 rounded border text-sm text-slate-600 hover:bg-slate-50 transition-colors">
                <Download className="w-4 h-4"/> CSV
            </a>
            <a href="http://localhost:8000/api/export/sqlite" className="flex items-center justify-center gap-2 py-2 px-4 rounded border text-sm text-slate-600 hover:bg-slate-50 transition-colors">
                <Download className="w-4 h-4"/> DB
            </a>
        </div>
      </div>

      {activeJobId && (
        <JobProgress 
          jobId={activeJobId} 
          onComplete={() => setActiveJobId(null)} 
        />
      )}
    </div>
  );
};
