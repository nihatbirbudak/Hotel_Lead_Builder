import React, { useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJob } from '../lib/api';

interface Props {
    activeJobId: string | null;
}

export const LogPanel: React.FC<Props> = ({ activeJobId }) => {
    const bottomRef = useRef<HTMLDivElement>(null);
    
    const { data: job } = useQuery({
        queryKey: ['job', activeJobId],
        queryFn: () => getJob(activeJobId!),
        enabled: !!activeJobId,
        refetchInterval: 1000,
    });

    useEffect(() => {
        if (job?.logs && job.logs.length > 0) {
            bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
    }, [job?.logs]);

    if (!activeJobId) return null;

    const latestProcessing = job?.logs
        ?.slice()
        .reverse()
        .find((log) => log.message?.startsWith('Processing:'));

    return (
        <div className="bg-slate-900 rounded-xl p-4 border border-slate-800 shadow-sm">
            <div className="flex items-center justify-between mb-2 pb-2 border-b border-slate-800">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Canlı Loglar</h4>
                <span className="text-xs text-slate-600 font-mono">{job?.job_id?.slice(0, 8) || '...'}...</span>
            </div>
            <div className="text-xs text-slate-400 mb-2">
                {job ? `İşlenen: ${job.done}/${job.total} | Bulunan: ${job.websites_found || 0} | Bulunamadı: ${job.websites_not_found || 0}` : 'İşlem başlatılıyor...'}
                {latestProcessing ? ` | Şu an: ${latestProcessing.message.replace('Processing: ', '')}` : ''}
                {!latestProcessing && job?.last_warning ? ` | Son uyarı: ${job.last_warning}` : ''}
            </div>
            <div className="h-48 overflow-auto custom-scrollbar font-mono text-xs space-y-1">
                {(!job || !job.logs || job.logs.length === 0) && (
                    <div className="text-slate-600 italic p-2">İşlem başlatılıyor...</div>
                )}
                {job?.logs?.map((log, idx) => (
                    <div key={idx} className="flex gap-2 hover:bg-white/5 p-0.5 rounded px-2">
                        <span className="text-slate-600 min-w-[70px]">
                            {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                        <span className={
                            log.level === 'ERROR' ? 'text-red-400 font-bold' : 
                            log.level === 'SUCCESS' ? 'text-emerald-400' : 
                            log.level === 'WARNING' ? 'text-amber-400' : 
                            'text-blue-300'
                        }>
                            {log.level}
                        </span>
                        <span className="text-slate-300 break-all">{log.message}</span>
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>
        </div>
    );
};
