import React from 'react';
import { useStore } from '../store';

export const LogPanel: React.FC = () => {
  const { logs } = useStore();

  return (
    <div className="mt-6 bg-slate-900 text-slate-300 rounded-xl p-4 h-48 overflow-auto custom-scrollbar font-mono text-xs">
      {logs.length === 0 && <div className="text-slate-600 italic">Sistem beklemede. Loglar burada görünecek.</div>}
      {logs.map(log => (
        <div key={log.id} className="mb-1 border-l-2 pl-2 border-transparent hover:bg-white/5 py-0.5 rounded"
             style={{ borderColor: log.type === 'error' ? '#ef4444' : log.type === 'success' ? '#22c55e' : log.type === 'warning' ? '#f59e0b' : '#3b82f6' }}>
          <span className="text-slate-500 mr-2">[{log.timestamp.toLocaleTimeString()}]</span>
          <span className={
            log.type === 'error' ? 'text-red-400' : 
            log.type === 'success' ? 'text-green-400' : 
            log.type === 'warning' ? 'text-amber-400' : 'text-blue-300'
          }>
            {log.message}
          </span>
        </div>
      ))}
    </div>
  );
};
