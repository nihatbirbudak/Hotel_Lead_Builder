import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Facility, getDocumentTypes } from '../lib/api';
import { Globe, Mail, CheckCircle, XCircle, Loader2, Bug, Search, AlertCircle } from 'lucide-react';

type TabType = 'pending' | 'not_found' | 'has_website' | 'has_email';

interface Props {
  data: Facility[];
  total: number;
  page: number;
  setPage: (p: number) => void;
  filters: any;
  setFilters: (f: any) => void;
  isLoading: boolean;
  selectedIds: string[];
  setSelectedIds: (ids: string[]) => void;
  activeTab?: TabType;
}

export const HotelTable: React.FC<Props> = ({ 
    data, total, page, setPage, filters, setFilters, isLoading, selectedIds, setSelectedIds, activeTab = 'pending'
}) => {
  const [showDebug, setShowDebug] = useState(false);
  
  // Load document types
  const { data: typesData } = useQuery({
    queryKey: ['documentTypes'],
    queryFn: async () => {
      const res = await getDocumentTypes();
      return res.data;
    },
  });

  const toggleSelect = (id: string) => {
      if (selectedIds.includes(id)) {
          setSelectedIds(selectedIds.filter(x => x !== id));
      } else {
          setSelectedIds([...selectedIds, id]);
      }
  };

  const toggleSelectAll = () => {
      const allOnPage = data.map(d => d.id);
      const allSelected = allOnPage.every(id => selectedIds.includes(id));
      
      if (allSelected) {
          // Deselect all on this page
          setSelectedIds(selectedIds.filter(id => !allOnPage.includes(id)));
      } else {
          // Select all on this page
          const combined = Array.from(new Set([...selectedIds, ...allOnPage]));
          setSelectedIds(combined);
      }
  };

  const isAllSelected = data.length > 0 && data.every(d => selectedIds.includes(d.id));
  
  // Count how many selected items are visible on current page
  const selectedOnPage = data.filter(d => selectedIds.includes(d.id)).length;
  
  // Tab-based styling
  const tabColors = {
    pending: { border: 'border-slate-200', accent: 'text-slate-600', bg: 'bg-slate-50' },
    not_found: { border: 'border-orange-200', accent: 'text-orange-600', bg: 'bg-orange-50' },
    has_website: { border: 'border-blue-200', accent: 'text-blue-600', bg: 'bg-blue-50' },
    has_email: { border: 'border-green-200', accent: 'text-green-600', bg: 'bg-green-50' }
  };
  const colors = tabColors[activeTab];
  
  // Empty state messages per tab
  const emptyMessages = {
    pending: { icon: Search, text: 'Aranacak tesis yok', subtext: 'Tüm tesisler zaten arandı' },
    not_found: { icon: AlertCircle, text: 'Bulunamayan tesis yok', subtext: 'Tüm aranan tesislerin websiteleri bulundu' },
    has_website: { icon: Globe, text: 'Website bulunan tesis yok', subtext: 'Henüz website bulunamadı. Discovery job başlatın.' },
    has_email: { icon: Mail, text: 'Email bulunan tesis yok', subtext: 'Henüz email bulunamadı. Email crawl job başlatın.' }
  };
  const emptyState = emptyMessages[activeTab];

  return (
    <div className={`bg-white rounded-b-xl shadow-sm border ${colors.border} flex flex-col min-h-[500px]`}>
       <div className="p-4 border-b border-slate-200 flex gap-3 bg-slate-50 items-center flex-wrap">
         <input 
            className="border rounded px-3 py-1.5 text-sm w-64 focus:ring-2 focus:ring-brand-500 outline-none" 
            placeholder="Tesis veya Şehir ara..." 
            value={filters.search}
            onChange={e => setFilters({...filters, search: e.target.value})}
         />
         <input 
            className="border rounded px-3 py-1.5 text-sm w-48 focus:ring-2 focus:ring-brand-500 outline-none" 
            placeholder="Şehir filtresi..." 
            value={filters.city}
            onChange={e => setFilters({...filters, city: e.target.value})}
         />
         
         <select 
            className="border rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 outline-none"
            value={filters.type || ''}
            onChange={e => setFilters({...filters, type: e.target.value || undefined})}
         >
            <option value="">Tüm Belge Türleri</option>
            {typesData?.types?.map((t: any) => (
              <option key={t.name} value={t.name}>
                {t.name} ({t.count})
              </option>
            ))}
         </select>
         
         <div className="ml-auto">
            <button 
                onClick={() => setShowDebug(!showDebug)}
                className={`p-2 rounded hover:bg-slate-200 transition-colors ${showDebug ? 'text-brand-600 bg-slate-200' : 'text-slate-400'}`}
                title="Toggle Debug View"
            >
                <Bug className="w-4 h-4" />
            </button>
         </div>
       </div>

        {/* Debug Row */}
        {showDebug && data.length > 0 && (
            <div className="bg-slate-900 p-4 border-b border-slate-800 animate-in fade-in slide-in-from-top-2">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-slate-400 uppercase">First Row Raw Data (Debug)</span>
                    <span className="text-xs font-mono text-slate-500">ID: {data[0].id}</span>
                </div>
                <pre className="text-xs font-mono text-emerald-400 overflow-auto max-h-60 custom-scrollbar whitespace-pre-wrap break-all">
                    {JSON.stringify(data[0], null, 2)}
                </pre>
            </div>
        )}

       <div className="flex-1 overflow-auto custom-scrollbar">
         <table className="w-full text-left text-sm text-slate-600">
           <thead className="bg-slate-50 sticky top-0 shadow-sm z-10">
             <tr>
               <th className="px-4 py-3 w-8">
                   <input type="checkbox" checked={isAllSelected} onChange={toggleSelectAll} className="rounded border-slate-300" />
               </th>
               <th className="px-4 py-3 font-semibold text-slate-700">Tesis Adı</th>
               <th className="px-4 py-3 font-semibold text-slate-700">Şehir</th>
               <th className="px-4 py-3 font-semibold text-slate-700">İlçe</th>
               <th className="px-4 py-3 font-semibold text-slate-700">Website</th>
               <th className="px-4 py-3 font-semibold text-slate-700">Email</th>
               <th className="px-4 py-3 font-semibold text-slate-700 text-center">Skor</th>
             </tr>
           </thead>
           <tbody className="divide-y divide-slate-100">
             {isLoading && (
               <tr>
                 <td colSpan={7} className="p-8 text-center text-slate-500">
                   <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2"/>
                   Yükleniyor...
                 </td>
               </tr>
             )}
             {!isLoading && data.length === 0 && (
               <tr>
                 <td colSpan={7} className="p-12 text-center">
                   <emptyState.icon className={`w-12 h-12 mx-auto mb-3 ${colors.accent} opacity-50`} />
                   <p className="text-slate-700 font-medium">{emptyState.text}</p>
                   <p className="text-slate-400 text-sm mt-1">{emptyState.subtext}</p>
                 </td>
               </tr>
             )}
             {!isLoading && data.map(row => (
               <tr key={row.id} className={`hover:bg-slate-50 transition-colors ${selectedIds.includes(row.id) ? 'bg-blue-50/50' : ''}`}>
                 <td className="px-4 py-2">
                     <input 
                        type="checkbox" 
                        checked={selectedIds.includes(row.id)} 
                        onChange={() => toggleSelect(row.id)}
                        className="rounded border-slate-300"
                     />
                 </td>
                 <td className="px-4 py-2 font-medium text-slate-900">
                    {row.name || row.tesis_adi || "İsimsiz Tesis"}
                    <div className="text-xs text-slate-400 font-normal">{row.type || row.belge_turu}</div>
                 </td>
                 <td className="px-4 py-2">{row.sehir || row.city || ""}</td>
                 <td className="px-4 py-2 text-slate-500">{row.ilce || row.district || ""}</td>
                 <td className="px-4 py-2">
                   {row.website ? (
                     <a href={row.website} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline flex items-center gap-1 max-w-[12rem] truncate">
                        <Globe className="w-3 h-3 flex-shrink-0"/> {new URL(row.website).hostname.replace('www.','')}
                     </a>
                   ) : (
                        row.website_status === 'not_found' 
                        ? <span className="text-slate-300 flex items-center gap-1"><XCircle className="w-3 h-3"/> Yok</span>
                        : <span className="text-slate-300">-</span>
                   )}
                 </td>
                 <td className="px-4 py-2">
                    {row.email ? (
                        <a href={`mailto:${row.email}`} className="flex items-center gap-1 text-emerald-700 hover:underline max-w-[12rem] truncate">
                            <Mail className="w-3 h-3 flex-shrink-0"/> {row.email}
                        </a>
                    ) : (
                        row.email_status === 'not_found' 
                        ? <span className="text-slate-300 flex items-center gap-1"><XCircle className="w-3 h-3"/> Yok</span>
                        : <span className="text-slate-300">-</span>
                    )}
                 </td>
                 <td className="px-4 py-2 text-center">
                    {row.website_score ? (
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${row.website_score > 70 ? 'bg-green-100 text-green-700' : row.website_score > 40 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-50 text-red-600'}`}>
                            {Math.round(row.website_score)}
                        </span>
                    ) : <span className="text-slate-300">-</span>}
                 </td>
               </tr>
             ))}
           </tbody>
         </table>
       </div>

       <div className="p-4 border-t flex justify-between items-center bg-slate-50">
         <button disabled={page===1} onClick={() => setPage(page-1)} className="px-3 py-1 border rounded bg-white text-sm hover:bg-slate-100 disabled:opacity-50">Önceki</button>
         <div className="flex items-center gap-4">
            <span className="text-sm text-slate-600">Sayfa {page} / {Math.ceil(total/50) || 1}</span>
            {selectedIds.length > 0 && (
                <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold bg-brand-100 text-brand-700 px-2 py-1 rounded">
                        {selectedIds.length} Seçildi
                        {selectedOnPage > 0 && selectedOnPage < selectedIds.length && (
                            <span className="text-brand-500 ml-1">(bu sayfada {selectedOnPage})</span>
                        )}
                    </span>
                    <button 
                        onClick={() => setSelectedIds([])}
                        className="text-xs text-red-600 hover:text-red-800 hover:underline"
                    >
                        Temizle
                    </button>
                </div>
            )}
         </div>
         <button disabled={page >= Math.ceil(total/50)} onClick={() => setPage(page+1)} className="px-3 py-1 border rounded bg-white text-sm hover:bg-slate-100 disabled:opacity-50">Sonraki</button>
       </div>
    </div>
  );
};
