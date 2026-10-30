import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN;

// Mapbox needs absolute URLs for GeoJSON sources.
const abs = (u) => new URL(u, window.location.origin).toString();

export default function MapView({ apiBase }) {
  const ref = useRef(null);

  useEffect(() => {
    const map = new mapboxgl.Map({
      container: ref.current,
      style: import.meta.env.VITE_MAPBOX_STYLE || 'mapbox://styles/mapbox/satellite-streets-v12',
      center: [72.36, 34.95],   // Mingora / Swat valley
      zoom: 9.5,
      pitch: 45,                 // 3D valley view
    });
    map.addControl(new mapboxgl.NavigationControl(), 'top-right');
    map.addControl(new mapboxgl.ScaleControl(), 'bottom-left');

    map.on('style.load', () => {
      map.addSource('dem', { type: 'raster-dem', url: 'mapbox://mapbox.mapbox-terrain-dem-v1', tileSize: 512 });
      map.setTerrain({ source: 'dem', exaggeration: 1.3 });
    });

    map.on('load', () => {
      map.addSource('reaches', { type: 'geojson', data: abs(`${apiBase}/reaches`) });
      map.addLayer({
        id: 'reaches-fill', type: 'fill', source: 'reaches',
        paint: { 'fill-color': '#1f6feb', 'fill-opacity': 0.25 },
      });

      map.addSource('alerts', { type: 'geojson', data: abs(`${apiBase}/alerts?status=new`) });
      map.addLayer({
        id: 'alerts-fill', type: 'fill', source: 'alerts',
        paint: { 'fill-color': '#e5484d', 'fill-opacity': 0.6 },
      });

      map.on('click', 'alerts-fill', (e) => {
        const p = e.features[0].properties;
        new mapboxgl.Popup()
          .setLngLat(e.lngLat)
          .setHTML(`<b>Alert ${p.id}</b><br/>Δ ${Number(p.db_change).toFixed(2)} dB<br/>coh loss ${Number(p.coh_loss).toFixed(2)}`)
          .addTo(map);
      });
    });

    return () => map.remove();
  }, [apiBase]);

  return <div ref={ref} className="absolute inset-0" />;
}
