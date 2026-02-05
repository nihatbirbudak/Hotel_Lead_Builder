'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, Clock, TrendingUp, Zap } from 'lucide-react';
import { getJob } from '../lib/api';

interface Job {
  job_id: string;
  status: string;
  total: number;
  done: number;
  errors: number;
  websites_found: number;
  websites_not_found: number;
  success_rate: number;
  created_at: string;
  finished_at: string;
  elapsed_seconds: number;
  estimated_remaining_seconds: number;
  logs: any[];
  current_action?: string | null;
  current_item?: string | null;
  last_success?: string | null;
  last_warning?: string | null;
}

interface JobProgressProps {
  jobId?: string;
  onComplete?: () => void;
}

export default function JobProgress({ jobId, onComplete }: JobProgressProps) {
  const [showDetails, setShowDetails] = useState(false);

  const { data: job, isLoading } = useQuery<Job>({
    queryKey: ['job', jobId],
    queryFn: () => getJob(jobId!),
    enabled: !!jobId,
    refetchInterval: jobId ? 1000 : false, // Poll every second
    onSuccess: (data) => {
      if (data.status === 'completed' && onComplete) {
        onComplete();
      }
    },
  });

  if (!jobId || !job) return null;

  const progress = job.total > 0 ? (job.done / job.total) * 100 : 0;
  const isRunning = job.status === 'running';
  const isCompleted = job.status === 'completed';
  const isFailed = job.status === 'failed';

  // Format time
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins === 0) return `${secs}s`;
    return `${mins}m ${secs}s`;
  };

  // Recent logs
  const recentLogs = job.logs?.slice(-10) || [];

  return (
    <div className="fixed bottom-4 right-4 w-96 bg-white border border-gray-200 rounded-lg shadow-xl p-6 z-50 max-h-96 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {isRunning && <Zap className="w-5 h-5 text-blue-500 animate-pulse" />}
          {isCompleted && <CheckCircle2 className="w-5 h-5 text-green-500" />}
          {isFailed && <AlertCircle className="w-5 h-5 text-red-500" />}
          <h3 className="font-semibold text-gray-800">
            {isRunning && 'Discovery İşlemi Devam Ediyor'}
            {isCompleted && 'Discovery Tamamlandı'}
            {isFailed && 'Discovery Başarısız'}
          </h3>
        </div>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
        >
          {showDetails ? 'Gizle' : 'Detaylar'}
        </button>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-gray-600 font-medium">
            İşlem: {job.done}/{job.total}
          </span>
          <span className="text-sm font-semibold text-gray-800">
            {Math.round(progress)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div
            className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {(job.current_item || job.last_success || job.last_warning) && (
        <div className="mb-4 text-xs text-gray-600">
          {job.current_item && (
            <div>Su an: {job.current_item}</div>
          )}
          {!job.current_item && job.last_success && (
            <div>Son basarili: {job.last_success}</div>
          )}
          {!job.current_item && !job.last_success && job.last_warning && (
            <div>Son durum: {job.last_warning}</div>
          )}
        </div>
      )}

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        {/* Bulunanlar */}
        <div className="bg-green-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle2 className="w-4 h-4 text-green-600" />
            <span className="text-xs text-gray-600">Bulunanlar</span>
          </div>
          <p className="text-lg font-bold text-green-600">{job.websites_found}</p>
        </div>

        {/* Bulunamayanlar */}
        <div className="bg-amber-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <AlertCircle className="w-4 h-4 text-amber-600" />
            <span className="text-xs text-gray-600">Bulunamadı</span>
          </div>
          <p className="text-lg font-bold text-amber-600">{job.websites_not_found || 0}</p>
        </div>

        {/* Başarı Oranı */}
        <div className="bg-blue-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-blue-600" />
            <span className="text-xs text-gray-600">Başarı</span>
          </div>
          <p className="text-lg font-bold text-blue-600">{job.success_rate}%</p>
        </div>

        {/* Zaman */}
        <div className="bg-orange-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Clock className="w-4 h-4 text-orange-600" />
            <span className="text-xs text-gray-600">Geçen</span>
          </div>
          <p className="text-lg font-bold text-orange-600">
            {formatTime(job.elapsed_seconds)}
          </p>
        </div>
      </div>

      {/* Remaining Time (if running) */}
      {isRunning && job.estimated_remaining_seconds > 0 && (
        <div className="mb-4 p-3 bg-amber-50 rounded-lg">
          <p className="text-sm text-gray-700">
            <span className="font-medium">Tahmini kalan:</span>{' '}
            <span className="font-bold text-amber-600">
              {formatTime(job.estimated_remaining_seconds)}
            </span>
          </p>
        </div>
      )}

      {/* Details Section */}
      {showDetails && (
        <div className="border-t pt-4">
          {/* Summary */}
          <div className="mb-4">
            <h4 className="font-semibold text-gray-700 mb-2 text-sm">Özet</h4>
            <div className="space-y-1 text-sm text-gray-600">
              <p>
                <span className="font-medium">Toplam:</span> {job.total}
              </p>
              <p>
                <span className="font-medium">İşlenen:</span> {job.done}
              </p>
              <p>
                <span className="font-medium">Website Bulundu:</span> {job.websites_found}
              </p>
              <p>
                <span className="font-medium">Hata:</span>{' '}
                <span className={job.errors > 0 ? 'text-red-600' : 'text-green-600'}>
                  {job.errors}
                </span>
              </p>
            </div>
          </div>

          {/* Recent Logs */}
          {recentLogs.length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-2 text-sm">Son Loglar</h4>
              <div className="bg-gray-50 rounded p-2 max-h-40 overflow-y-auto space-y-1">
                {recentLogs.map((log, idx) => (
                  <div
                    key={idx}
                    className={`text-xs font-mono p-1 rounded ${
                      log.level === 'ERROR'
                        ? 'bg-red-100 text-red-800'
                        : log.level === 'SUCCESS'
                          ? 'bg-green-100 text-green-800'
                          : log.level === 'WARNING'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-blue-100 text-blue-800'
                    }`}
                  >
                    [{log.level}] {log.message}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Status Footer */}
      <div className="mt-4 pt-4 border-t text-xs text-gray-500 text-center">
        {isRunning && 'İşlem devam ediyor...'}
        {isCompleted && 'Başarıyla tamamlandı!'}
        {isFailed && 'İşlem başarısız oldu!'}
      </div>
    </div>
  );
}
