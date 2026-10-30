import { useEffect, useState } from 'react';
import MapView from './components/MapView.jsx';

const API = import.meta.env.VITE_API_URL ?? '/api';

export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetch(`${API}/health`).then((r) => r.json()).then(setHealth).catch(() => setHealth({ ok: false }));
  }, []);

  return (
    <div className="flex h-full">
      <aside className="w-80 shrink-0 border-r border-slate-200 bg-white p-4 overflow-y-auto">
        <h1 className="text-lg font-semibold text-slate-900">SUVASTU</h1>
        <p className="mt-1 text-sm text-slate-500">Reaches, SAR change alerts, extraction blocks</p>
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs">
          API: {health ? (health.ok ? <span className="text-green-600">connected</span> : <span className="text-alert">down</span>) : '...'}
        </div>
      </aside>
      <main className="relative flex-1">
        <MapView apiBase={API} />
      </main>
    </div>
  );
}
