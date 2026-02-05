'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { getJob, cancelJob } from '../../../lib/api';

interface Props {
  params: { id: string };
}

export default function JobDetailPage({ params }: Props) {
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [cancelSuccess, setCancelSuccess] = useState(false);
  const queryClient = useQueryClient();
  
  const { data: job, isLoading } = useQuery({
    queryKey: ['job', params.id],
    queryFn: () => getJob(params.id),
    refetchInterval: 2000,
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelJob(params.id),
    onSuccess: () => {
      setCancelSuccess(true);
      setCancelError(null);
      queryClient.invalidateQueries({ queryKey: ['job', params.id] });
    },
    onError: (error: any) => {
      setCancelError(error?.response?.data?.detail || 'Durdurma başarısız');
    }
  });

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-slate-900">Is Detayi</h1>
          </div>
          <Link href="/jobs" className="text-sm text-brand-600 hover:text-brand-700">
            Is Gecmisi
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {isLoading && (
          <div className="text-sm text-slate-500">Yukleniyor...</div>
        )}

        {!isLoading && !job && (
          <div className="text-sm text-slate-500">Is bulunamadi.</div>
        )}

        {job && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 space-y-4">
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
                <div className="text-xs text-slate-500">Job ID</div>
                <div className="font-mono text-sm text-slate-800 break-all">{job.job_id}</div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
                <div className="text-xs text-slate-500">Durum</div>
                <div className="text-sm font-semibold text-slate-800">{job.status}</div>
                {(job.status === 'running' || job.status === 'queued') && (
                  <button
                    onClick={() => cancelMutation.mutate()}
                    disabled={cancelMutation.isPending}
                    className="mt-3 w-full px-3 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white text-sm rounded-lg transition"
                  >
                    {cancelMutation.isPending ? 'Durduriliyor...' : 'Durdur'}
                  </button>
                )}
                {cancelSuccess && (
                  <div className="mt-2 text-xs text-emerald-600 bg-emerald-50 p-2 rounded">
                    İş durduruldu.
                  </div>
                )}
                {cancelError && (
                  <div className="mt-2 text-xs text-red-600 bg-red-50 p-2 rounded">
                    {cancelError}
                  </div>
                )}
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
                <div className="text-xs text-slate-500">Ozet</div>
                <div className="text-sm text-slate-800">Islenen: {job.done}/{job.total}</div>
                <div className="text-sm text-emerald-700">Bulunan: {job.websites_found || 0}</div>
                <div className="text-sm text-amber-700">Bulunamadi: {job.websites_not_found || 0}</div>
                <div className="text-sm text-slate-800">Basari: {job.success_rate}%</div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
                <div className="text-xs text-slate-500">Bulunamadi Nedenleri</div>
                {!job.not_found_reasons || job.not_found_reasons.length === 0 && (
                  <div className="text-sm text-slate-500">Henuz veri yok.</div>
                )}
                {job.not_found_reasons?.map((item: any, idx: number) => (
                  <div key={idx} className="text-sm text-slate-700">
                    {item.reason} ({item.count})
                  </div>
                ))}
              </div>
            </div>

            <div className="lg:col-span-2">
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
                <div className="text-sm font-bold text-slate-700 mb-3">Loglar</div>
                <div className="h-96 overflow-auto text-xs font-mono space-y-1">
                  {!job.logs || job.logs.length === 0 && (
                    <div className="text-slate-500">Log bulunamadi.</div>
                  )}
                  {job.logs?.map((log: any, idx: number) => (
                    <div key={idx} className="flex gap-2">
                      <span className="text-slate-500 min-w-[70px]">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                      <span className={
                        log.level === 'ERROR' ? 'text-red-600' :
                        log.level === 'SUCCESS' ? 'text-emerald-600' :
                        log.level === 'WARNING' ? 'text-amber-600' :
                        'text-blue-600'
                      }>
                        {log.level}
                      </span>
                      <span className="text-slate-700 break-all">{log.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
