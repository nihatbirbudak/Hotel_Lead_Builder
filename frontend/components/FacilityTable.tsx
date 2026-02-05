import React from 'react';
import { Facility } from '../lib/api';
import { Globe, Mail, CheckCircle, XCircle, Loader2 } from 'lucide-react';

interface Props {
  data: Facility[];
  total: number;
  page: number;
  setPage: (p: number) => void;
  filters: any;
  setFilters: (f: any) => void;
  isLoading: boolean;
}

export const FacilityTable: React.FC<Props> = ({ data, total, page, setPage, filters, setFilters, isLoading }) => {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col min-h-[600px]">
       <div className="p-4 border-b border-slate-200 flex gap-4 bg-slate-50 rounded-t-xl">
         <input 
            className="border rounded px-3 py-1.5 text-sm w-64" 
            placeholder="Arama yap..." 
            value={filters.search}
            onChange={e => setFilters({...filters, search: e.target.value})}
         />
       </div>

       <div className="flex-1 overflow-auto">
         <table className="w-full text-left text-sm text-slate-600">
           <thead className="bg-slate-50 sticky top-0">
             <tr>
               <th className="px-4 py-3">Tesis Adı</th>
               <th className="px-4 py-3">Şehir</th>
               <th className="px-4 py-3">Website</th>
               <th className="px-4 py-3">Email</th>
               <th className="px-4 py-3">Skor</th>
             </tr>
           </thead>
           <tbody className="divide-y divide-slate-100">
             {isLoading && <tr><td colSpan={5} className="p-4 text-center">Yükleniyor...</td></tr>}
             {!isLoading && data.map(row => (
               <tr key={row.id} className="hover:bg-slate-50">
                 <td className="px-4 py-2 font-medium">{row.name}</td>
                 <td className="px-4 py-2">{row.city}</td>
                 <td className="px-4 py-2">
                   {row.website ? (
                     <a href={row.website} target="_blank" className="text-blue-600 flex items-center gap-1">
                        <Globe className="w-3 h-3"/> {new URL(row.website).hostname}
                     </a>
                   ) : <span className="text-slate-300">-</span>}
                 </td>
                 <td className="px-4 py-2">
                    {row.email ? (
                        <div className="flex items-center gap-1 text-green-700">
                            <Mail className="w-3 h-3"/> {row.email}
                        </div>
                    ) : <span className="text-slate-300">-</span>}
                 </td>
                 <td className="px-4 py-2">
                    {row.website_score ? Math.round(row.website_score) : 0}
                 </td>
               </tr>
             ))}
           </tbody>
         </table>
       </div>

       <div className="p-4 border-t flex justify-between items-center">
         <button disabled={page===1} onClick={() => setPage(page-1)} className="px-3 py-1 border rounded disabled:opacity-50">Önceki</button>
         <span>Sayfa {page} / {Math.ceil(total/50)}</span>
         <button disabled={page >= Math.ceil(total/50)} onClick={() => setPage(page+1)} className="px-3 py-1 border rounded disabled:opacity-50">Sonraki</button>
       </div>
    </div>
  );
};
