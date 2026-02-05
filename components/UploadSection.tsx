import React, { useRef } from 'react';
import { Upload, FileText, AlertCircle } from 'lucide-react';
import { parseTGAFile, mapRawDataToHotel } from '../utils';
import { useStore } from '../store';

export const UploadSection: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { setHotels, addLog } = useStore();

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    addLog(`Dosya yükleniyor: ${file.name}`, 'info');

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const content = event.target?.result as string;
        const rawData = parseTGAFile(content);
        
        if (!rawData || rawData.length === 0) {
          addLog("Dosya içeriği boş veya geçersiz format.", 'error');
          return;
        }

        const mappedData = rawData.map(mapRawDataToHotel);
        setHotels(mappedData);
        addLog(`${mappedData.length} tesis başarıyla yüklendi.`, 'success');
      } catch (error) {
        addLog("Dosya işlenirken hata oluştu: " + (error as Error).message, 'error');
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 mb-6">
      <div className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-lg p-10 hover:bg-slate-50 transition-colors cursor-pointer"
           onClick={() => fileInputRef.current?.click()}>
        <Upload className="w-12 h-12 text-slate-400 mb-4" />
        <h3 className="text-lg font-medium text-slate-900">raw_tga.txt dosyasını buraya bırakın</h3>
        <p className="text-slate-500 mt-2 text-sm">veya seçmek için tıklayın (JSON formatı)</p>
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleFileUpload} 
          accept=".txt,.json" 
          className="hidden" 
        />
      </div>
      <div className="mt-4 flex items-start gap-2 text-xs text-slate-500 bg-blue-50 p-3 rounded text-blue-800">
        <AlertCircle className="w-4 h-4 mt-0.5" />
        <p>
          Not: Sistem tarayıcı tabanlı çalışır. Veriler yerel bellekte tutulur. 
          Website ve Email tarama işlemleri için internet bağlantısı ve isteğe bağlı Gemini API anahtarı gerektirir.
        </p>
      </div>
    </div>
  );
};
