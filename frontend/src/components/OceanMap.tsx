import React, { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import { Thermometer, Droplets, Anchor, RefreshCw, Globe } from 'lucide-react';
import api from '../lib/api';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import 'leaflet.markercluster';
import L from 'leaflet';

interface GlobalFloat {
  float_id: string;
  lat: number;
  lon: number;
  temperature: number | null;
  salinity: number | null;
  pressure: number | null;
  timestamp: string | null;
  sources?: string[];
}

interface DataSummary {
  total_profiles: number;
  total_floats: number;
  temperature_range: { min: number | null; max: number | null; avg: number | null };
  salinity_range: { min: number | null; max: number | null; avg: number | null };
}

const getColor = (temp: number | null): string => {
  if (temp === null) return '#6b7280';
  if (temp < 5) return '#3b82f6';
  if (temp < 15) return '#06b6d4';
  if (temp < 25) return '#f59e0b';
  return '#ef4444';
};

/** Clustered marker layer using Leaflet API directly */
const ClusteredMarkers: React.FC<{ floats: GlobalFloat[] }> = ({ floats }) => {
  const map = useMap();
  const clusterRef = useRef<L.MarkerClusterGroup | null>(null);

  useEffect(() => {
    if (!map) return;

    if (clusterRef.current) {
      map.removeLayer(clusterRef.current);
      clusterRef.current = null;
    }

    const cluster = (L as any).markerClusterGroup({
      maxClusterRadius: 45,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      disableClusteringAtZoom: 8,
      chunkedLoading: true,
      chunkInterval: 100,
      chunkDelay: 10,
      iconCreateFunction: (c: any) => {
        const count = c.getChildCount();
        let size = 'small';
        let dim = 28;
        if (count > 100) { size = 'large'; dim = 38; }
        else if (count > 30) { size = 'medium'; dim = 32; }
        return L.divIcon({
          html: `<div style="
            width:${dim}px;height:${dim}px;
            display:flex;align-items:center;justify-content:center;
            border-radius:50%;
            font-size:${size === 'large' ? 11 : 9}px;font-weight:700;
            color:#fff;
            background:${size === 'large' ? 'rgba(6,182,212,0.85)' : size === 'medium' ? 'rgba(6,182,212,0.75)' : 'rgba(6,182,212,0.65)'};
            border:2px solid rgba(255,255,255,0.4);
            box-shadow:0 2px 8px rgba(0,0,0,0.4);
          ">${count}</div>`,
          className: '',
          iconSize: L.point(dim, dim),
        });
      },
    });

    const markers = floats.map(f => {
      const color = getColor(f.temperature);
      const icon = L.divIcon({
        html: `<div style="
          width:8px;height:8px;border-radius:50%;
          background:${color};border:1.5px solid #fff;
          box-shadow:0 1px 4px rgba(0,0,0,0.5);
        "></div>`,
        className: '',
        iconSize: L.point(8, 8),
        iconAnchor: L.point(4, 4),
      });
      const m = L.marker([f.lat, f.lon], { icon });
      const ts = f.timestamp ? new Date(f.timestamp).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : 'N/A';
      m.bindPopup(
        `<div style="font-family:system-ui;font-size:12px;line-height:1.6;min-width:160px">
          <div style="font-weight:700;font-size:13px;color:#0e7490;margin-bottom:4px">Float ${f.float_id}</div>
          <div style="border-top:1px solid #e2e8f0;padding-top:4px">
            <b>Lat:</b> ${f.lat.toFixed(3)}°<br/>
            <b>Lon:</b> ${f.lon.toFixed(3)}°<br/>
            ${f.temperature != null ? `<b>Temp:</b> ${f.temperature.toFixed(1)}°C<br/>` : ''}
            ${f.salinity != null ? `<b>Salinity:</b> ${f.salinity.toFixed(2)} PSU<br/>` : ''}
            ${f.pressure != null ? `<b>Pressure:</b> ${f.pressure.toFixed(0)} dbar<br/>` : ''}
            ${f.sources?.length ? `<b>Type:</b> ${f.sources.map(s => s.replace('argo_', '')).join(', ')}<br/>` : ''}
            <b>Last update:</b> ${ts}
          </div>
        </div>`,
        { maxWidth: 220 }
      );
      return m;
    });

    cluster.addLayers(markers);
    map.addLayer(cluster);
    clusterRef.current = cluster;

    return () => {
      if (clusterRef.current) {
        map.removeLayer(clusterRef.current);
        clusterRef.current = null;
      }
    };
  }, [map, floats]);

  return null;
};

/** Force Leaflet to recalculate size after container renders */
const InvalidateSize: React.FC = () => {
  const map = useMap();
  useEffect(() => {
    const ro = new ResizeObserver(() => map.invalidateSize());
    ro.observe(map.getContainer());
    const t = setTimeout(() => map.invalidateSize(), 300);
    return () => { ro.disconnect(); clearTimeout(t); };
  }, [map]);
  return null;
};

export const OceanMap: React.FC = () => {
  const [globalFloats, setGlobalFloats] = useState<GlobalFloat[]>([]);
  const [floatCount, setFloatCount] = useState(0);
  const [summary, setSummary] = useState<DataSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [globalRes, summaryRes] = await Promise.allSettled([
        api.get('/analytics/global-floats'),
        api.get('/data/summary'),
      ]);
      if (globalRes.status === 'fulfilled') {
        setGlobalFloats(globalRes.value.data.floats || []);
        setFloatCount(globalRes.value.data.count || 0);
      }
      if (summaryRes.status === 'fulfilled') {
        setSummary(summaryRes.value.data);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const stats = [
    { label: 'Profiles', value: summary?.total_profiles?.toLocaleString() ?? '—', icon: <Anchor className="w-4 h-4" /> },
    { label: 'Floats', value: floatCount > 0 ? floatCount.toLocaleString() : (summary?.total_floats ?? '—'), icon: <Droplets className="w-4 h-4" /> },
    { label: 'Avg Temp', value: summary?.temperature_range.avg ? `${summary.temperature_range.avg.toFixed(1)}°C` : '—', icon: <Thermometer className="w-4 h-4" /> },
    { label: 'Avg Salinity', value: summary?.salinity_range.avg ? `${summary.salinity_range.avg.toFixed(1)} PSU` : '—', icon: <Droplets className="w-4 h-4" /> },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Stat cards */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-white/10 bg-slate-900/60 flex-shrink-0 overflow-x-auto">
        {stats.map((s) => (
          <div key={s.label} className="flex items-center gap-2 bg-slate-800/60 rounded-lg px-3 py-2 min-w-fit">
            <span className="text-cyan-400">{s.icon}</span>
            <div className="leading-none">
              <p className="text-[11px] text-slate-400">{s.label}</p>
              <p className="text-sm font-semibold">{s.value}</p>
            </div>
          </div>
        ))}

        <button
          onClick={loadData}
          className="ml-auto flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors px-3 py-2 rounded-lg hover:bg-white/5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Map */}
      <div className="flex-1 relative">
        {isLoading && globalFloats.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-900">
            <div className="text-center space-y-3">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-cyan-400 border-t-transparent mx-auto" />
              <p className="text-sm text-slate-400">Loading global floats…</p>
            </div>
          </div>
        ) : (
          <MapContainer center={[20, 0]} zoom={2} scrollWheelZoom={true} style={{ height: '100%', width: '100%', background: '#1a1a2e' }}>
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution='&copy; <a href="https://carto.com/">CARTO</a>'
              maxZoom={18}
            />
            <ClusteredMarkers floats={globalFloats} />
            <InvalidateSize />
          </MapContainer>
        )}

        {/* Float count badge */}
        {floatCount > 0 && (
          <div className="absolute top-3 right-3 z-[1000] bg-slate-900/80 backdrop-blur-sm rounded-lg px-3 py-1.5 text-[11px] text-cyan-300 flex items-center gap-1.5 pointer-events-none">
            <Globe className="w-3 h-3" />
            {floatCount.toLocaleString()} active floats
          </div>
        )}

        {/* Legend */}
        <div className="absolute bottom-4 left-4 z-[1000] flex items-center gap-3 bg-slate-900/80 backdrop-blur-sm rounded-lg px-3 py-2 text-xs">
          <span className="text-slate-300 font-medium">Temp:</span>
          {[
            { color: '#3b82f6', label: '< 5°C' },
            { color: '#06b6d4', label: '5–15°C' },
            { color: '#f59e0b', label: '15–25°C' },
            { color: '#ef4444', label: '> 25°C' },
          ].map((l) => (
            <span key={l.label} className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: l.color }} />
              {l.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
