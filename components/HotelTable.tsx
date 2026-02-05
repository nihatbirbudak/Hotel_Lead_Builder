import React, { useMemo, useState } from 'react';
import { useStore } from '../store';
import { Globe, Mail, Search, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Hotel } from '../types';

export const HotelTable: React.FC = () => {
  const { filteredHotels, filters, setFilter } = useStore();
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 50;

  // Filter Options logic
  const cities = useMemo(() => {
    const list = filteredHotels.map(h => h.il).filter((c): c is string => !!c);
    return Array.from(new Set(list)).sort() as string[];
  }, [filteredHotels]);

  const types = useMemo(() => {
    const list = filteredHotels.map(h => h.tur).filter((t): t is string => !!t);
    return Array.from(new Set(list)).sort() as string[];
  }, [filteredHotels]);

  const totalPages = Math.ceil(filteredHotels.length / itemsPerPage);
  const currentData = filteredHotels.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const getStatusIcon = (status: Hotel['status']) => {
    switch (status) {
      case 'searching_web':
      case 'scanning_email':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
      case 'web_found':
      case 'email_found':
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'web_failed':
      case 'email_failed':
        return <XCircle className="w-4 h-4 text-red-400" />;
      default:
        return <div className="w-2 h-2 rounded-full bg-slate-300" />;
    }
  };

  if (filteredHotels.length === 0 && filters.search === '' && filters.city === '') {
    return null; // Don't show empty table if no data loaded yet
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col h-[600px]">
      {/* Filters Toolbar */}
      <div className="p-4 border-b border-slate-200 flex gap-4 flex-wrap bg-slate-50 rounded-t-xl">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input 
            type="text" 
            placeholder="Tesis veya Şehir Ara..." 
            className="pl-9 pr-4 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 w-64"
            value={filters.search}
            onChange={(e) => setFilter('search', e.target.value)}
          />
        </div>
        
        <select 
          className="px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
          value={filters.city}
          onChange={(e) => setFilter('city', e.target.value)}
        >
          <option value="">Tüm Şehirler</option>
          {cities.map(c => <option key={c} value={c}>{c}</option>)}
        </select>

        <select 
          className="px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white max-w-xs truncate"
          value={filters.type}
          onChange={(e) => setFilter('type', e.target.value)}
        >
          <option value="">Tüm Türler</option>
          {types.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        
        <div className="ml-auto flex items-center text-sm text-slate-500">
          Toplam: <span className="font-semibold text-slate-900 ml-1">{filteredHotels.length}</span>
        </div>
      </div>

      {/* Table Content */}
      <div className="flex-1 overflow-auto custom-scrollbar relative">
        <table className="w-full text-left text-sm text-slate-600">
          <thead className="bg-slate-50 text-slate-700 font-medium sticky top-0 z-10 shadow-sm">
            <tr>
              <th className="px-4 py-3 w-10">#</th>
              <th className="px-4 py-3">Tesis Adı</th>
              <th className="px-4 py-3 w-32">Şehir</th>
              <th className="px-4 py-3 w-32">İlçe</th>
              <th className="px-4 py-3 w-48">Belge Türü</th>
              <th className="px-4 py-3 w-48">Website</th>
              <th className="px-4 py-3 w-48">Email</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {currentData.map((hotel, idx) => (
              <tr key={hotel.id} className="hover:bg-slate-50 transition-colors group">
                <td className="px-4 py-3 flex items-center justify-center">
                    {getStatusIcon(hotel.status)}
                </td>
                <td className="px-4 py-3 font-medium text-slate-900">{hotel.ad}</td>
                <td className="px-4 py-3">{hotel.il}</td>
                <td className="px-4 py-3">{hotel.ilce}</td>
                <td className="px-4 py-3 text-xs text-slate-500 truncate max-w-[12rem]" title={hotel.tur}>{hotel.tur}</td>
                <td className="px-4 py-3">
                  {hotel.website ? (
                    <a href={hotel.website} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-blue-600 hover:underline max-w-[10rem] truncate">
                      <Globe className="w-3 h-3" /> {new URL(hotel.website).hostname.replace('www.', '')}
                    </a>
                  ) : (
                    <span className="text-slate-300">-</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {hotel.email ? (
                    <a href={`mailto:${hotel.email}`} className="flex items-center gap-1 text-slate-700 hover:text-blue-600 max-w-[10rem] truncate">
                      <Mail className="w-3 h-3" /> {hotel.email}
                    </a>
                  ) : (
                    <span className="text-slate-300">-</span>
                  )}
                </td>
              </tr>
            ))}
            {currentData.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-slate-400">Veri bulunamadı.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="p-3 border-t border-slate-200 flex justify-between items-center bg-slate-50 rounded-b-xl">
        <button 
          onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
          disabled={currentPage === 1}
          className="px-3 py-1 border border-slate-300 rounded bg-white text-sm disabled:opacity-50 hover:bg-slate-100"
        >
          Önceki
        </button>
        <span className="text-sm text-slate-600">Sayfa {currentPage} / {totalPages || 1}</span>
        <button 
          onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
          disabled={currentPage === totalPages || totalPages === 0}
          className="px-3 py-1 border border-slate-300 rounded bg-white text-sm disabled:opacity-50 hover:bg-slate-100"
        >
          Sonraki
        </button>
      </div>
    </div>
  );
};