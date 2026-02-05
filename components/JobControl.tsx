import React, { useEffect, useState } from 'react';
import { useStore } from '../store';
import { Play, Pause, Download, Database, Key, Activity } from 'lucide-react';
import { findWebsiteWithDDG, findWebsiteWithGemini, findEmailOnPage } from '../services/discoveryService';
import { CONCURRENCY_LIMIT } from '../constants';
import { exportToCSV, exportToSQL } from '../utils';

export const JobControl: React.FC = () => {
  const { 
    hotels, 
    filteredHotels, 
    isJobRunning, 
    jobProgress, 
    setJobStatus, 
    updateHotel, 
    addLog 
  } = useStore();
  
  const [apiKey, setApiKey] = useState('');
  const [useGemini, setUseGemini] = useState(false);

  // Stats
  const foundWebsites = hotels.filter(h => h.website).length;
  const foundEmails = hotels.filter(h => h.email).length;

  // Job Runner Logic (Simplified Queue)
  useEffect(() => {
    let active = true;

    const processQueue = async () => {
      if (!isJobRunning || !active) return;

      const targetList = filteredHotels; // Operate on filtered view
      const jobType = jobProgress.jobType;

      if (!jobType) return;

      // Find pending items
      const pendingItems = targetList.filter(h => {
        if (jobType === 'discovery') return !h.website && h.status !== 'web_failed' && h.status !== 'web_found';
        if (jobType === 'email_harvest') return h.website && !h.email && h.status !== 'email_failed' && h.status !== 'email_found';
        return false;
      });

      if (pendingItems.length === 0) {
        setJobStatus(false);
        addLog(`${jobType === 'discovery' ? 'Website keşfi' : 'Email toplama'} tamamlandı.`, 'success');
        return;
      }

      // Take a batch
      const batch = pendingItems.slice(0, CONCURRENCY_LIMIT);

      await Promise.all(batch.map(async (hotel) => {
        if (!active) return;

        try {
          if (jobType === 'discovery') {
            updateHotel(hotel.id, { status: 'searching_web' });
            
            let url = null;
            if (useGemini && apiKey) {
                // IMPORTANT: In a real app, we shouldn't set process.env on client side like this, 
                // but we need to pass the key to the service. 
                process.env.API_KEY = apiKey; 
                url = await findWebsiteWithGemini(hotel.ad, hotel.il);
            } else {
                url = await findWebsiteWithDDG(hotel.ad, hotel.il);
            }

            if (url) {
              updateHotel(hotel.id, { website: url, status: 'web_found', websiteSource: useGemini ? 'gemini' : 'duckduckgo' });
              addLog(`Website bulundu: ${hotel.ad} -> ${url}`, 'success', hotel.id);
            } else {
              updateHotel(hotel.id, { status: 'web_failed' });
              addLog(`Website bulunamadı: ${hotel.ad}`, 'warning', hotel.id);
            }
          } 
          else if (jobType === 'email_harvest') {
            updateHotel(hotel.id, { status: 'scanning_email' });
            if (!hotel.website) {
                updateHotel(hotel.id, { status: 'email_failed' });
                return;
            }
            
            const email = await findEmailOnPage(hotel.website);
            
            if (email) {
              updateHotel(hotel.id, { email: email, status: 'email_found', emailSource: 'scrape' });
              addLog(`Email bulundu: ${hotel.ad} -> ${email}`, 'success', hotel.id);
            } else {
              updateHotel(hotel.id, { status: 'email_failed' });
              addLog(`Email bulunamadı: ${hotel.ad}`, 'warning', hotel.id);
            }
          }
        } catch (e) {
          addLog(`Hata (${hotel.ad}): ${(e as Error).message}`, 'error', hotel.id);
        }
      }));
      
      // Update progress
      const currentCompleted = jobType === 'discovery' 
        ? targetList.filter(h => h.website || h.status === 'web_failed').length
        : targetList.filter(h => h.email || h.status === 'email_failed').length;

      setJobStatus(true, jobType, currentCompleted, targetList.length);
      
      // Loop
      if (active && isJobRunning) {
        setTimeout(processQueue, 1000); // Small delay to be polite
      }
    };

    if (isJobRunning) {
        processQueue();
    }

    return () => { active = false; };
  }, [isJobRunning, filteredHotels, jobProgress.jobType, apiKey, useGemini]);

  const toggleJob = (type: 'discovery' | 'email_harvest') => {
    if (isJobRunning) {
      setJobStatus(false);
      addLog("İşlem kullanıcı tarafından durduruldu.", 'warning');
    } else {
      if (type === 'discovery' && useGemini && !apiKey) {
          alert("Gemini Modu için API Anahtarı giriniz.");
          return;
      }
      addLog(`${type === 'discovery' ? 'Website keşfi' : 'Email toplama'} başlatıldı...`, 'info');
      setJobStatus(true, type, 0, filteredHotels.length);
    }
  };

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 sticky top-6">
      <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
        <Activity className="w-5 h-5 text-brand-500" />
        Kontrol Paneli
      </h3>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-blue-50 p-3 rounded-lg border border-blue-100">
          <div className="text-xs text-blue-600 font-medium uppercase">Websites</div>
          <div className="text-2xl font-bold text-blue-900">{foundWebsites}</div>
        </div>
        <div className="bg-green-50 p-3 rounded-lg border border-green-100">
          <div className="text-xs text-green-600 font-medium uppercase">Emails</div>
          <div className="text-2xl font-bold text-green-900">{foundEmails}</div>
        </div>
      </div>

      {/* Settings */}
      <div className="mb-6 space-y-3">
         <label className="flex items-center gap-2 text-sm text-slate-700 font-medium cursor-pointer">
            <input type="checkbox" checked={useGemini} onChange={e => setUseGemini(e.target.checked)} className="rounded text-brand-500" />
            Gemini AI "Akıllı Arama" Kullan
         </label>
         
         {useGemini && (
             <div className="flex items-center gap-2 border border-slate-300 rounded px-2 py-1 bg-white">
                 <Key className="w-4 h-4 text-slate-400" />
                 <input 
                    type="password" 
                    placeholder="Gemini API Key" 
                    value={apiKey}
                    onChange={e => setApiKey(e.target.value)}
                    className="flex-1 text-sm outline-none"
                 />
             </div>
         )}
      </div>

      {/* Actions */}
      <div className="space-y-3">
        <button 
          onClick={() => toggleJob('discovery')}
          className={`w-full flex items-center justify-center gap-2 py-3 rounded-lg font-medium transition-colors ${
            isJobRunning && jobProgress.jobType === 'discovery'
              ? 'bg-red-50 text-red-600 border border-red-200 hover:bg-red-100'
              : 'bg-brand-600 text-white hover:bg-brand-700'
          }`}
        >
          {isJobRunning && jobProgress.jobType === 'discovery' ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          {isJobRunning && jobProgress.jobType === 'discovery' ? 'Durdur' : 'Website Bul (Auto)'}
        </button>

        <button 
          onClick={() => toggleJob('email_harvest')}
          disabled={foundWebsites === 0}
          className={`w-full flex items-center justify-center gap-2 py-3 rounded-lg font-medium transition-colors ${
            isJobRunning && jobProgress.jobType === 'email_harvest'
              ? 'bg-red-50 text-red-600 border border-red-200 hover:bg-red-100'
              : 'bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed'
          }`}
        >
          {isJobRunning && jobProgress.jobType === 'email_harvest' ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          {isJobRunning && jobProgress.jobType === 'email_harvest' ? 'Durdur' : 'Email Topla'}
        </button>

        <hr className="border-slate-100 my-4" />

        <div className="grid grid-cols-2 gap-2">
            <button 
              onClick={() => exportToCSV(hotels)}
              disabled={hotels.length === 0}
              className="flex items-center justify-center gap-2 py-2 px-4 rounded border border-slate-300 text-slate-600 hover:bg-slate-50 text-sm disabled:opacity-50"
            >
              <Download className="w-4 h-4" /> CSV
            </button>
            <button 
              onClick={() => exportToSQL(hotels)}
              disabled={hotels.length === 0}
              className="flex items-center justify-center gap-2 py-2 px-4 rounded border border-slate-300 text-slate-600 hover:bg-slate-50 text-sm disabled:opacity-50"
            >
              <Database className="w-4 h-4" /> SQL
            </button>
        </div>
      </div>
        
      {/* Progress Bar */}
      {isJobRunning && (
          <div className="mt-4">
              <div className="flex justify-between text-xs text-slate-500 mb-1">
                  <span>İlerleme</span>
                  <span>{jobProgress.current} / {jobProgress.total}</span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-brand-500 transition-all duration-300" 
                    style={{ width: `${(jobProgress.current / jobProgress.total) * 100}%` }}
                  />
              </div>
          </div>
      )}
    </div>
  );
};
