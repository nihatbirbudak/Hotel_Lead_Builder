import React, { useRef, useState } from 'react';
import { Upload, AlertCircle } from 'lucide-react';
import { uploadFile } from '../lib/api';

export const UploadSection: React.FC<{onUploadSuccess: () => void}> = ({onUploadSuccess}) => {
    const ref = useRef<HTMLInputElement>(null);
    const [loading, setLoading] = useState(false);
    const [reset, setReset] = useState(false);

    const handle = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files?.[0]) return;
        setLoading(true);
        try {
            const res = await uploadFile(e.target.files[0], reset);
            const { inserted, updated, total_rows, reset_applied } = res.data;
            alert(`Yükleme Başarılı!\n\nToplam Satır: ${total_rows}\nYeni Eklenen: ${inserted}\nGüncellenen: ${updated}\nVeritabanı Sıfırlandı: ${reset_applied ? 'Evet' : 'Hayır'}`);
            onUploadSuccess();
        } catch(err) {
            console.error(err);
            alert("Yükleme sırasında bir hata oluştu. Lütfen dosya formatını ve backend loglarını kontrol edin.");
        }
        setLoading(false);
        // Clear input
        if (ref.current) ref.current.value = '';
    };

    return (
        <div className="bg-white p-8 rounded-xl border-2 border-dashed border-slate-300 flex flex-col items-center justify-center hover:bg-slate-50 transition-colors">
            <div className="bg-slate-100 p-4 rounded-full mb-4">
                <Upload className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-medium text-slate-900 mb-1">Veri Seti Yükle</h3>
            <p className="text-sm text-slate-500 mb-6">raw_tga.txt veya JSON dosyasını buraya sürükleyin</p>
            
            <div className="flex flex-col items-center gap-4 w-full max-w-xs">
                <button 
                    onClick={() => ref.current?.click()} 
                    disabled={loading} 
                    className="w-full py-2.5 bg-slate-900 text-white rounded-lg font-medium hover:bg-slate-800 disabled:opacity-50 shadow-lg shadow-slate-900/20 transition-all"
                >
                    {loading ? 'Yükleniyor...' : 'Dosya Seç'}
                </button>
                
                <div className="flex items-center gap-2 cursor-pointer" onClick={() => setReset(!reset)}>
                    <input 
                        type="checkbox" 
                        checked={reset} 
                        onChange={e => setReset(e.target.checked)} 
                        className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                    />
                    <label className="text-sm text-slate-600 select-none">Mevcut veritabanını temizle</label>
                </div>
            </div>
            
            <input type="file" ref={ref} onChange={handle} className="hidden" accept=".txt,.json" />
        </div>
    );
};
