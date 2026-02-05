import React from 'react';
import { UploadSection } from './components/UploadSection';
import { HotelTable } from './components/HotelTable';
import { JobControl } from './components/JobControl';
import { LogPanel } from './components/LogPanel';
import { useStore } from './store';
import { Building2 } from 'lucide-react';

const App: React.FC = () => {
  const { hotels } = useStore();
  const hasData = hotels.length > 0;

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-brand-600 rounded-lg flex items-center justify-center shadow-lg shadow-brand-500/30">
              <Building2 className="text-white w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 leading-tight">Hotel Lead Builder</h1>
              <p className="text-xs text-slate-500 font-medium">Local Data Intelligence Tool</p>
            </div>
          </div>
          <div className="text-xs text-slate-400 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
            v1.0.0 • Client-Side Only
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          
          {/* Left / Main Column */}
          <div className="lg:col-span-3 space-y-6">
            {!hasData && <UploadSection />}
            {hasData && <HotelTable />}
            <LogPanel />
          </div>

          {/* Right / Sidebar */}
          <div className="lg:col-span-1">
             {hasData ? (
                <JobControl />
             ) : (
                <div className="bg-white p-6 rounded-xl border border-slate-200 text-center text-slate-400">
                   <p className="text-sm">Veri yüklendikten sonra kontrol paneli aktif olacaktır.</p>
                </div>
             )}
          </div>

        </div>
      </main>
    </div>
  );
};

export default App;
