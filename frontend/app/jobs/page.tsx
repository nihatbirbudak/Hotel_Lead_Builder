'use client';

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listJobs, cancelJob } from '../../lib/api';
import Link from 'next/link';

export default function JobsPage() {
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['jobs'],
    queryFn: async () => {
      console.log('Fetching jobs from API...');
      try {
        const result = await listJobs();
        console.log('Jobs result:', result);
        
        // Dummy test - verify structure
        if (!result || !result.jobs) {
          console.warn('Result structure invalid:', result);
          return { jobs: [] };
        }
        
        return result;
      } catch (err: any) {
        console.error('Query fetch error:', err?.message || err);
        return { jobs: [] }; // Don't throw, return empty
      }
    },
    initialData: { jobs: [] },
    refetchInterval: 3000,
    staleTime: 1000,
    retry: false,
    enabled: true,
  });

  // Fallback loading state to false after 10 seconds to debug
  const cancelMutation = useMutation({
    mutationFn: (jobId: string) => cancelJob(jobId),
    onSuccess: () => {
      setCancellingId(null);
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
    onError: () => {
      setCancellingId(null);
    }
  });

  const handleCancel = (jobId: string) => {
    setCancellingId(jobId);
    cancelMutation.mutate(jobId);
  };

  const jobs = data?.jobs || [];

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-slate-900">Is Gecmisi</h1>
          </div>
          <Link href="/" className="text-sm text-brand-600 hover:text-brand-700">
            Ana Sayfa
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-300 rounded text-sm text-red-800 font-mono break-all">
            <div className="font-bold">ERROR:</div>
            <div>{String(error instanceof Error ? error.message : error)}</div>
            <div className="text-xs mt-1 opacity-70">{String(error)}</div>
          </div>
        )}
        
        <div className="bg-white rounded-xl shadow-sm border border-slate-200">
          <div className="p-4 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-700">Son Isler</h2>
            <span className="text-xs text-slate-500">{jobs.length} kayit</span>
          </div>

          {isLoading && (
            <div className="p-6 text-sm text-slate-500">Yukleniyor...</div>
          )}

          {!isLoading && jobs.length === 0 && (
            <div className="p-6 text-sm text-slate-500">Henuz is yok.</div>
          )}

          {!isLoading && jobs.length > 0 && (
            <div className="overflow-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-slate-600">
                  <tr>
                    <th className="text-left px-4 py-3">Tip</th>
                    <th className="text-left px-4 py-3">Durum</th>
                    <th className="text-left px-4 py-3">Islenen</th>
                    <th className="text-left px-4 py-3">Bulunan</th>
                    <th className="text-left px-4 py-3">Bulunamadi</th>
                    <th className="text-left px-4 py-3">Basari</th>
                    <th className="text-left px-4 py-3">Sure</th>
                    <th className="text-left px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {jobs.map((job) => (
                    <tr key={job.job_id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <Link href={`/jobs/${job.job_id}`} className="font-medium text-slate-800 hover:text-brand-600">
                          {job.job_type}
                        </Link>
                        <div className="text-xs text-slate-500">{job.job_id.slice(0, 8)}...</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-xs ${
                          job.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                          job.status === 'running' ? 'bg-blue-100 text-blue-700' :
                          job.status === 'failed' ? 'bg-red-100 text-red-700' :
                          job.status === 'cancelled' ? 'bg-slate-100 text-slate-600' :
                          'bg-slate-100 text-slate-600'
                        }`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">{job.done}/{job.total}</td>
                      <td className="px-4 py-3 text-emerald-700">{job.websites_found || 0}</td>
                      <td className="px-4 py-3 text-amber-700">{job.websites_not_found || 0}</td>
                      <td className="px-4 py-3">{job.success_rate || 0}%</td>
                      <td className="px-4 py-3">{job.elapsed_seconds || 0}s</td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {(job.status === 'running' || job.status === 'queued') && (
                          <button
                            onClick={() => handleCancel(job.job_id)}
                            disabled={cancellingId === job.job_id}
                            className="px-2 py-1 bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white text-xs rounded"
                          >
                            {cancellingId === job.job_id ? 'Durduriliyor...' : 'Durdur'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
