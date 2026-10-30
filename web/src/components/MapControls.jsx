import { useEffect, useState } from 'react';
import { LuMinus, LuNavigation2, LuPlus } from 'react-icons/lu';

const buttonClass =
  'flex size-[26px] cursor-pointer items-center justify-center text-white transition-colors ' +
  'hover:bg-river focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-bar';

export default function MapControls({ map }) {
  const [bearing, setBearing] = useState(0);

  useEffect(() => {
    if (!map) return;
    const sync = () => setBearing(map.getBearing());
    map.on('rotate', sync);
    return () => map.off('rotate', sync);
  }, [map]);

  return (
    <div className="absolute top-2.5 right-2.5 z-10 divide-y divide-white/15 overflow-hidden rounded-lg border border-white/15 bg-[var(--map-panel)] shadow-lg backdrop-blur-[10px]">
      <button type="button" className={buttonClass} title="Zoom in" aria-label="Zoom in" onClick={() => map?.zoomIn()}>
        <LuPlus size={14} />
      </button>
      <button type="button" className={buttonClass} title="Zoom out" aria-label="Zoom out" onClick={() => map?.zoomOut()}>
        <LuMinus size={14} />
      </button>
      {/* Keeps the 3D pitch; only the bearing resets */}
      <button type="button" className={buttonClass} title="Reset north" aria-label="Reset north" onClick={() => map?.resetNorth()}>
        <LuNavigation2 size={14} fill="currentColor" style={{ transform: `rotate(${-bearing}deg)` }} />
      </button>
    </div>
  );
}
