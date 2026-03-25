import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import Plot from 'react-plotly.js';
import {
  MapContainer, TileLayer, Rectangle, useMap, useMapEvents,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import 'leaflet.markercluster';
import {
  Thermometer, Droplets, Anchor, Layers, ChevronDown, ChevronRight,
  Globe, Activity, Clock, MapPin, Lightbulb, X, Waves,
  Target, Compass,
} from 'lucide-react';
import api from '../lib/api';

/* ================================================================
   TYPES
   ================================================================ */
interface BBox { min_lat: number; max_lat: number; min_lon: number; max_lon: number }

interface RegionSummary {
  total_profiles: number;
  total_floats: number;
  temperature?: { min: number; max: number; avg: number } | null;
  salinity?: { min: number; max: number; avg: number } | null;
  depth?: { min: number; max: number; avg: number } | null;
  bounds?: { min_lat: number; max_lat: number; min_lon: number; max_lon: number } | null;
}

interface AnalyticsData {
  count: number;
  temperature: (number | null)[];
  salinity: (number | null)[];
  depth: (number | null)[];
  pressure: (number | null)[];
  latitude: number[];
  longitude: number[];
  timestamp: (string | null)[];
  float_id: (string | null)[];
  temp_stats?: Stats;
  sal_stats?: Stats;
  depth_stats?: { mean: number; median: number; std: number; min: number; max: number };
  ts_correlation?: number;
  unique_floats?: string[];
}

interface Stats {
  mean: number; median: number; std: number; min: number; max: number; q1: number; q3: number;
}

interface MapPt { lat: number; lon: number; temperature: number | null; salinity: number | null; float_id: string | null }

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

/* ================================================================
   CONSTANTS
   ================================================================ */
const PLOTLY_LAYOUT_BASE: any = {
  autosize: true,
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(15,23,42,0.4)',
  font: { color: '#cbd5e1', size: 11 },
  margin: { t: 32, r: 16, b: 44, l: 52 },
};

const PLOTLY_CFG: any = { responsive: true, displayModeBar: false };

const GRID = '#1e293b';

/* ================================================================
   INSIGHT GENERATORS
   ================================================================ */
function tempInsights(d: AnalyticsData): string[] {
  const s = d.temp_stats;
  if (!s) return [];
  const out: string[] = [];
  out.push(`Temperature ranges from ${s.min.toFixed(1)}\u00B0C to ${s.max.toFixed(1)}\u00B0C with a mean of ${s.mean.toFixed(1)}\u00B0C.`);
  if (s.q3 - s.q1 < 5) out.push(`Most readings cluster between ${s.q1.toFixed(1)}\u00B0C and ${s.q3.toFixed(1)}\u00B0C, indicating a narrow thermal band \u2014 likely dominated by one water mass.`);
  else out.push(`The wide interquartile range (${s.q1.toFixed(1)}\u00B0C \u2013 ${s.q3.toFixed(1)}\u00B0C) reveals multiple thermal layers or mixing between water masses.`);
  if (s.mean < 5) out.push(`The low average temperature suggests predominantly deep-ocean or high-latitude measurements.`);
  else if (s.mean > 20) out.push(`The warm average indicates tropical or subtropical surface waters.`);
  return out;
}

function salInsights(d: AnalyticsData): string[] {
  const s = d.sal_stats;
  if (!s) return [];
  const out: string[] = [];
  out.push(`Salinity ranges from ${s.min.toFixed(2)} to ${s.max.toFixed(2)} PSU with a mean of ${s.mean.toFixed(2)} PSU.`);
  if (s.std < 0.5) out.push(`Low variability (\u03C3 = ${s.std.toFixed(2)}) indicates a well-mixed water column or a single dominant water mass.`);
  else out.push(`High variability (\u03C3 = ${s.std.toFixed(2)}) suggests mixing between fresher and saltier water sources.`);
  if (s.min < 34) out.push(`Values below 34 PSU may indicate freshwater influence from rivers, melting ice, or precipitation.`);
  return out;
}

function oceanInsights(d: AnalyticsData): string[] {
  const out: string[] = [];
  if (d.ts_correlation !== undefined) {
    const r = d.ts_correlation;
    const desc = Math.abs(r) > 0.7 ? 'strong' : Math.abs(r) > 0.4 ? 'moderate' : 'weak';
    out.push(`Temperature\u2013Salinity correlation is ${desc} (r = ${r.toFixed(3)}).`);
    if (r > 0.4) out.push(`The positive correlation suggests warmer, saltier subtropical water dominates this region.`);
    else if (r < -0.4) out.push(`The negative correlation points to high-latitude mixing where fresher water tends to be warmer (e.g., meltwater near the surface).`);
  }
  out.push(`Clusters on the T\u2013S diagram represent distinct water masses. Tight clusters indicate homogeneous water; spread patterns reveal active mixing.`);
  return out;
}

function depthInsights(d: AnalyticsData): string[] {
  const s = d.depth_stats;
  if (!s) return [];
  const out: string[] = [];
  out.push(`Profiles reach depths of ${s.min.toFixed(0)} m to ${s.max.toFixed(0)} m (mean ${s.mean.toFixed(0)} m).`);
  if (s.max > 1500) out.push(`Deep measurements (> 1500 m) capture the entire water column, useful for understanding thermohaline circulation.`);
  out.push(`The thermocline \u2014 the layer of rapid temperature change \u2014 typically appears between 200\u20131000 m depth.`);
  return out;
}

function temporalInsights(d: AnalyticsData): string[] {
  const ts = d.timestamp.filter(Boolean) as string[];
  if (ts.length < 2) return ['Insufficient temporal data for trend analysis.'];
  const dates = ts.map(t => new Date(t).getTime());
  const spanDays = (Math.max(...dates) - Math.min(...dates)) / 86400000;
  const out: string[] = [];
  out.push(`Data spans approximately ${Math.round(spanDays)} days.`);
  if (spanDays > 365) out.push(`Multi-year coverage enables detection of seasonal and inter-annual variability patterns.`);
  else if (spanDays > 90) out.push(`This covers enough time to detect seasonal temperature shifts and transient events.`);
  else out.push(`The short time window captures a snapshot rather than seasonal trends.`);
  return out;
}

function geoInsights(d: AnalyticsData): string[] {
  const floats = d.unique_floats || [];
  const out: string[] = [];
  out.push(`Data covers ${floats.length} autonomous ARGO float(s) across ${d.count.toLocaleString()} measurements.`);
  const latRange = Math.max(...d.latitude) - Math.min(...d.latitude);
  const lonRange = Math.max(...d.longitude) - Math.min(...d.longitude);
  if (latRange > 60) out.push(`Wide latitudinal spread (${latRange.toFixed(0)}\u00B0) captures multiple climate zones from polar to tropical waters.`);
  if (lonRange > 90) out.push(`Broad longitudinal coverage (${lonRange.toFixed(0)}\u00B0) spans multiple ocean basins.`);
  return out;
}

/* ================================================================
   SUB-COMPONENTS
   ================================================================ */

/** Collapsible section wrapper */
const Section: React.FC<{
  title: string; icon: React.ReactNode; color: string;
  defaultOpen?: boolean; count?: number; children: React.ReactNode;
}> = ({ title, icon, color, defaultOpen = false, count, children }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-white/5 rounded-2xl overflow-hidden bg-slate-900/40">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-white/[0.02] transition-colors"
      >
        <span className={`p-2 rounded-xl ${color}`}>{icon}</span>
        <span className="flex-1 text-[15px] font-semibold text-slate-200">{title}</span>
        {count !== undefined && <span className="text-xs text-slate-500 bg-slate-800 rounded-full px-2.5 py-0.5">{count} charts</span>}
        {open ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
      </button>
      {open && <div className="px-5 pb-5 pt-1 space-y-4">{children}</div>}
    </div>
  );
};

/** Single chart card */
const ChartCard: React.FC<{ title: string; description: string; children: React.ReactNode }> = ({ title, description, children }) => (
  <div className="bg-slate-800/40 border border-white/5 rounded-xl p-4">
    <h4 className="text-sm font-semibold text-slate-200 mb-0.5">{title}</h4>
    <p className="text-[11px] text-slate-500 mb-3 leading-relaxed">{description}</p>
    {children}
  </div>
);

/** Insight panel */
const InsightBox: React.FC<{ insights: string[] }> = ({ insights }) => {
  if (!insights.length) return null;
  return (
    <div className="bg-gradient-to-br from-cyan-500/5 via-slate-800/30 to-transparent border border-cyan-500/10 rounded-xl px-4 py-3 mt-2">
      <div className="flex items-center gap-2 mb-2">
        <Lightbulb className="w-3.5 h-3.5 text-cyan-400" />
        <span className="text-[11px] font-semibold text-cyan-400 uppercase tracking-wider">AI Insight</span>
      </div>
      <ul className="space-y-1">
        {insights.map((ins, i) => (
          <li key={i} className="flex items-start gap-2 text-[12px] text-slate-400 leading-relaxed">
            <span className="mt-1.5 w-1 h-1 rounded-full bg-cyan-500/60 flex-shrink-0" />
            {ins}
          </li>
        ))}
      </ul>
    </div>
  );
};

/* ================================================================
   MAP \u2014 RECTANGLE SELECTION
   ================================================================ */
/** Force Leaflet to recalculate container size whenever container becomes visible or resizes */
const InvalidateSize: React.FC = () => {
  const map = useMap();
  useEffect(() => {
    const container = map.getContainer();
    // ResizeObserver fires when the container goes from 0-width (hidden) to visible
    const ro = new ResizeObserver(() => {
      window.setTimeout(() => map.invalidateSize(), 50);
    });
    ro.observe(container);
    // Also fire on initial mount with staggered delays
    const timers = [100, 400, 1000].map(ms =>
      window.setTimeout(() => map.invalidateSize(), ms)
    );
    return () => {
      ro.disconnect();
      timers.forEach(clearTimeout);
    };
  }, [map]);
  return null;
};

/** Clustered marker layer — adds/removes markers via Leaflet API directly */
const ClusteredMarkers: React.FC<{ floats: GlobalFloat[] }> = ({ floats }) => {
  const map = useMap();
  const clusterRef = useRef<L.MarkerClusterGroup | null>(null);

  useEffect(() => {
    if (!map) return;

    // Clean up previous cluster group
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

const SelectionMap: React.FC<{
  floats: GlobalFloat[];
  localPoints: MapPt[];
  bbox: BBox | null;
  onSelect: (b: BBox | null) => void;
  loading: boolean;
}> = ({ floats, localPoints, bbox, onSelect }) => {
  // Use global floats if available, otherwise fall back to local DB points
  const hasGlobal = floats.length > 0;
  return (
    <MapContainer center={[20, 0]} zoom={2} scrollWheelZoom={true} style={{ height: 420, width: '100%', background: '#1a1a2e' }} className="rounded-xl">
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        maxZoom={18}
      />
      {hasGlobal ? (
        <ClusteredMarkers floats={floats} />
      ) : (
        /* Fallback: render local DB points as simple circle markers */
        <ClusteredMarkers floats={localPoints.map(p => ({
          float_id: p.float_id || 'local',
          lat: p.lat, lon: p.lon,
          temperature: p.temperature,
          salinity: p.salinity,
          pressure: null, timestamp: null,
        }))} />
      )}
      {bbox && (
        <Rectangle
          bounds={[[bbox.min_lat, bbox.min_lon], [bbox.max_lat, bbox.max_lon]]}
          pathOptions={{ color: '#22d3ee', weight: 2, fillColor: '#22d3ee', fillOpacity: 0.08, dashArray: '6 4' }}
        />
      )}
      <DrawRectangle onSelect={onSelect} />
      <InvalidateSize />
    </MapContainer>
  );
};

/** Leaflet hook: shift+drag to select rectangle */
const DrawRectangle: React.FC<{ onSelect: (b: BBox | null) => void }> = ({ onSelect }) => {
  const map = useMap();
  const startRef = useRef<L.LatLng | null>(null);
  const rectRef = useRef<L.Rectangle | null>(null);
  const drawingRef = useRef(false);

  useMapEvents({
    mousedown(e: any) {
      if (!e.originalEvent.shiftKey) return;
      map.dragging.disable();
      drawingRef.current = true;
      startRef.current = e.latlng;
      if (rectRef.current) { map.removeLayer(rectRef.current); rectRef.current = null; }
    },
    mousemove(e: any) {
      if (!drawingRef.current || !startRef.current) return;
      const bounds = L.latLngBounds(startRef.current, e.latlng);
      if (rectRef.current) rectRef.current.setBounds(bounds);
      else {
        rectRef.current = L.rectangle(bounds, { color: '#22d3ee', weight: 2, fillColor: '#22d3ee', fillOpacity: 0.12, dashArray: '6 4' });
        rectRef.current.addTo(map);
      }
    },
    mouseup(e: any) {
      map.dragging.enable();
      if (!drawingRef.current || !startRef.current) return;
      drawingRef.current = false;
      const b = L.latLngBounds(startRef.current, e.latlng);
      if (rectRef.current) { map.removeLayer(rectRef.current); rectRef.current = null; }
      const sw = b.getSouthWest();
      const ne = b.getNorthEast();
      if (Math.abs(ne.lat - sw.lat) < 0.5 && Math.abs(ne.lng - sw.lng) < 0.5) return;
      onSelect({ min_lat: sw.lat, max_lat: ne.lat, min_lon: sw.lng, max_lon: ne.lng });
      startRef.current = null;
    },
  });
  return null;
};

function getColor(temp: number | null): string {
  if (temp === null) return '#6b7280';
  if (temp < 5) return '#3b82f6';
  if (temp < 15) return '#06b6d4';
  if (temp < 25) return '#f59e0b';
  return '#ef4444';
}

/* ================================================================
   MAIN COMPONENT
   ================================================================ */
export const VisualizationPanel: React.FC = () => {
  const [mapPoints, setMapPoints] = useState<MapPt[]>([]);
  const [globalFloats, setGlobalFloats] = useState<GlobalFloat[]>([]);
  const [globalLoading, setGlobalLoading] = useState(true);
  const [floatCount, setFloatCount] = useState<number>(0);
  const [bbox, setBbox] = useState<BBox | null>(null);
  const [summary, setSummary] = useState<RegionSummary | null>(null);
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Load global ARGO floats from ERDDAP (cached on server) */
  useEffect(() => {
    setGlobalLoading(true);
    api.get('/analytics/global-floats')
      .then(r => {
        setGlobalFloats(r.data.floats || []);
        setFloatCount(r.data.count || 0);
      })
      .catch(() => {
        // Fallback to local DB points if ERDDAP is unavailable
        api.get('/analytics/map-points?limit=5000')
          .then(r => setMapPoints(r.data.points))
          .catch(() => {});
      })
      .finally(() => setGlobalLoading(false));
  }, []);

  /* Fetch analytics based on bbox */
  const fetchAnalytics = useCallback(async (region: BBox | null) => {
    setLoading(true);
    setError(null);
    try {
      const params: any = { limit: 3000 };
      if (region) Object.assign(params, region);
      const [fullRes, summRes] = await Promise.all([
        api.get('/analytics/full', { params }),
        api.get('/analytics/region-summary', { params: region || {} }),
      ]);
      setData(fullRes.data);
      setSummary(summRes.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAnalytics(bbox); }, [bbox, fetchAnalytics]);

  const handleSelect = useCallback((b: BBox | null) => setBbox(b), []);
  const clearSelection = useCallback(() => setBbox(null), []);

  /* Derived arrays (non-null) */
  const temps = useMemo(() => (data?.temperature || []).filter((v): v is number => v !== null), [data]);
  const sals = useMemo(() => (data?.salinity || []).filter((v): v is number => v !== null), [data]);
  const depths = useMemo(() => (data?.depth || []).filter((v): v is number => v !== null), [data]);
  const lats = useMemo(() => data?.latitude || [], [data]);
  const lons = useMemo(() => data?.longitude || [], [data]);

  /* Paired arrays for charts needing two valid values */
  const tempDepthPairs = useMemo(() => {
    if (!data) return { t: [] as number[], d: [] as number[] };
    const t: number[] = [], d: number[] = [];
    for (let i = 0; i < data.count; i++) {
      if (data.temperature[i] != null && data.depth[i] != null) { t.push(data.temperature[i]!); d.push(data.depth[i]!); }
    }
    return { t, d };
  }, [data]);

  const salDepthPairs = useMemo(() => {
    if (!data) return { s: [] as number[], d: [] as number[] };
    const s: number[] = [], d: number[] = [];
    for (let i = 0; i < data.count; i++) {
      if (data.salinity[i] != null && data.depth[i] != null) { s.push(data.salinity[i]!); d.push(data.depth[i]!); }
    }
    return { s, d };
  }, [data]);

  const tsPairs = useMemo(() => {
    if (!data) return { t: [] as number[], s: [] as number[], d: [] as number[] };
    const t: number[] = [], s: number[] = [], d: number[] = [];
    for (let i = 0; i < data.count; i++) {
      if (data.temperature[i] != null && data.salinity[i] != null) {
        t.push(data.temperature[i]!);
        s.push(data.salinity[i]!);
        d.push(data.depth[i] ?? 0);
      }
    }
    return { t, s, d };
  }, [data]);

  const tempTimePairs = useMemo(() => {
    if (!data) return { ts: [] as string[], t: [] as number[] };
    const ts: string[] = [], t: number[] = [];
    for (let i = 0; i < data.count; i++) {
      if (data.timestamp[i] && data.temperature[i] != null) { ts.push(data.timestamp[i]!); t.push(data.temperature[i]!); }
    }
    return { ts, t };
  }, [data]);

  const salTimePairs = useMemo(() => {
    if (!data) return { ts: [] as string[], s: [] as number[] };
    const ts: string[] = [], s: number[] = [];
    for (let i = 0; i < data.count; i++) {
      if (data.timestamp[i] && data.salinity[i] != null) { ts.push(data.timestamp[i]!); s.push(data.salinity[i]!); }
    }
    return { ts, s };
  }, [data]);

  /* Thermocline: bucket by depth, find max gradient */
  const thermoclineData = useMemo(() => {
    if (tempDepthPairs.t.length < 20) return null;
    const paired = tempDepthPairs.t.map((t, i) => ({ t, d: tempDepthPairs.d[i] })).sort((a, b) => a.d - b.d);
    const bucketSize = 50;
    const maxD = paired[paired.length - 1].d;
    const buckets: { depth: number; temp: number }[] = [];
    for (let d = 0; d <= maxD; d += bucketSize) {
      const inBucket = paired.filter(p => p.d >= d && p.d < d + bucketSize);
      if (inBucket.length > 0) {
        buckets.push({ depth: d + bucketSize / 2, temp: inBucket.reduce((a, b) => a + b.t, 0) / inBucket.length });
      }
    }
    const gradients: { depth: number; gradient: number }[] = [];
    for (let i = 1; i < buckets.length; i++) {
      gradients.push({
        depth: (buckets[i].depth + buckets[i - 1].depth) / 2,
        gradient: Math.abs(buckets[i].temp - buckets[i - 1].temp) / bucketSize * 100,
      });
    }
    return { buckets, gradients };
  }, [tempDepthPairs]);

  /* Seasonal grouping */
  const seasonalData = useMemo(() => {
    if (!tempTimePairs.ts.length) return null;
    const seasons: Record<string, number[]> = { 'Winter (DJF)': [], 'Spring (MAM)': [], 'Summer (JJA)': [], 'Autumn (SON)': [] };
    tempTimePairs.ts.forEach((ts, i) => {
      const m = new Date(ts).getMonth();
      if (m === 11 || m <= 1) seasons['Winter (DJF)'].push(tempTimePairs.t[i]);
      else if (m <= 4) seasons['Spring (MAM)'].push(tempTimePairs.t[i]);
      else if (m <= 7) seasons['Summer (JJA)'].push(tempTimePairs.t[i]);
      else seasons['Autumn (SON)'].push(tempTimePairs.t[i]);
    });
    return seasons;
  }, [tempTimePairs]);

  /* Density estimation (\u03C3_t) simple UNESCO EOS-80 */
  const densityData = useMemo(() => {
    if (tsPairs.t.length < 5) return null;
    const sigma = tsPairs.t.map((t, i) => {
      const S = tsPairs.s[i];
      return 999.842594 + 6.793952e-2 * t - 9.095290e-3 * t * t + 1.001685e-4 * t * t * t
        + (0.824493 - 4.0899e-3 * t + 7.6438e-5 * t * t) * S
        + (-5.72466e-3 + 1.0227e-4 * t) * Math.pow(S, 1.5)
        + 4.8314e-4 * S * S - 1000;
    });
    return { t: tsPairs.t, s: tsPairs.s, sigma };
  }, [tsPairs]);

  /* ================================================================
     RENDER
     ================================================================ */
  if (error && !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-3 max-w-xs">
          <p className="text-sm text-red-400">{error}</p>
          <button onClick={() => fetchAnalytics(bbox)} className="text-sm text-cyan-400 hover:text-cyan-300 underline">Try again</button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      {/* \u2500\u2500 INTERACTIVE MAP \u2500\u2500 */}
      <div className="relative border border-white/10 rounded-xl overflow-hidden" style={{ height: 420, minHeight: 420 }}>
        <SelectionMap floats={globalFloats} localPoints={mapPoints} bbox={bbox} onSelect={handleSelect} loading={globalLoading} />

        {/* Float count badge */}
        {floatCount > 0 && (
          <div className="absolute top-3 right-3 z-[1000] bg-slate-900/80 backdrop-blur-sm rounded-lg px-3 py-1.5 text-[11px] text-cyan-300 flex items-center gap-1.5 pointer-events-none">
            <Globe className="w-3 h-3" />
            {floatCount.toLocaleString()} active floats
          </div>
        )}

        {/* Hint overlay */}
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[1000] bg-slate-900/80 backdrop-blur-sm rounded-lg px-4 py-2 text-[11px] text-slate-300 flex items-center gap-2 pointer-events-none">
          <Target className="w-3.5 h-3.5 text-cyan-400" />
          Hold <kbd className="bg-slate-700 rounded px-1.5 py-0.5 text-[10px] font-mono">Shift</kbd> + drag to select a region
        </div>

        {/* Selection badge */}
        {bbox && (
          <button
            onClick={clearSelection}
            className="absolute top-3 right-3 z-[1000] flex items-center gap-1.5 bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 text-[11px] px-3 py-1.5 rounded-lg backdrop-blur-sm hover:bg-cyan-500/30 transition-colors"
          >
            <Compass className="w-3 h-3" />
            Region selected · {(bbox.max_lat - bbox.min_lat).toFixed(1)}° × {(bbox.max_lon - bbox.min_lon).toFixed(1)}°
            <X className="w-3 h-3 ml-1" />
          </button>
        )}

        {/* Legend */}
        <div className="absolute bottom-3 left-3 z-[1000] flex items-center gap-2.5 bg-slate-900/80 backdrop-blur-sm rounded-lg px-3 py-1.5 text-[10px]">
          <span className="text-slate-400 font-medium">Temp:</span>
          {([['#3b82f6', '< 5\u00B0C'], ['#06b6d4', '5\u201315\u00B0C'], ['#f59e0b', '15\u201325\u00B0C'], ['#ef4444', '> 25\u00B0C']] as const).map(([c, l]) => (
            <span key={l} className="flex items-center gap-1 text-slate-400">
              <span className="w-2 h-2 rounded-full" style={{ background: c }} />{l}
            </span>
          ))}
        </div>

        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 z-[999] bg-slate-950/40 flex items-center justify-center">
            <div className="animate-spin rounded-full h-6 w-6 border-2 border-cyan-400 border-t-transparent" />
          </div>
        )}
      </div>

      {/* \u2500\u2500 CONTENT \u2500\u2500 */}
      <div className="px-4 py-5 md:px-8 lg:px-12 space-y-4">

        {/* \u2500\u2500 REGION SUMMARY \u2500\u2500 */}
        {summary && summary.total_profiles > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
            <SummaryCard icon={<Layers className="w-4 h-4" />} color="text-cyan-400" bg="bg-cyan-500/10" label="Profiles" value={summary.total_profiles.toLocaleString()} />
            <SummaryCard icon={<Anchor className="w-4 h-4" />} color="text-blue-400" bg="bg-blue-500/10" label="Floats" value={String(summary.total_floats)} />
            <SummaryCard icon={<Thermometer className="w-4 h-4" />} color="text-orange-400" bg="bg-orange-500/10" label="Avg Temperature" value={summary.temperature ? `${summary.temperature.avg.toFixed(1)}\u00B0C` : '\u2014'} sub={summary.temperature ? `${summary.temperature.min.toFixed(1)} \u2013 ${summary.temperature.max.toFixed(1)}\u00B0C` : undefined} />
            <SummaryCard icon={<Droplets className="w-4 h-4" />} color="text-sky-400" bg="bg-sky-500/10" label="Avg Salinity" value={summary.salinity ? `${summary.salinity.avg.toFixed(2)} PSU` : '\u2014'} sub={summary.salinity ? `${summary.salinity.min.toFixed(2)} \u2013 ${summary.salinity.max.toFixed(2)}` : undefined} />
            <SummaryCard icon={<Activity className="w-4 h-4" />} color="text-purple-400" bg="bg-purple-500/10" label="Depth Range" value={summary.depth ? `${summary.depth.min.toFixed(0)} \u2013 ${summary.depth.max.toFixed(0)} m` : '\u2014'} />
            <SummaryCard icon={<Globe className="w-4 h-4" />} color="text-emerald-400" bg="bg-emerald-500/10" label="Geo Bounds" value={summary.bounds ? `${summary.bounds.min_lat.toFixed(0)}\u00B0 \u2013 ${summary.bounds.max_lat.toFixed(0)}\u00B0 lat` : '\u2014'} sub={summary.bounds ? `${summary.bounds.min_lon.toFixed(0)}\u00B0 \u2013 ${summary.bounds.max_lon.toFixed(0)}\u00B0 lon` : undefined} />
          </div>
        )}

        {data && data.count > 0 ? (
          <div className="space-y-3">

            {/* \u2501\u2501\u2501 1. TEMPERATURE ANALYSIS \u2501\u2501\u2501 */}
            <Section title="Temperature Analysis" icon={<Thermometer className="w-4 h-4" />} color="bg-orange-500/15 text-orange-400" defaultOpen count={4}>
              <InsightBox insights={data ? tempInsights(data) : []} />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <ChartCard title="Temperature Distribution" description="Frequency of temperature readings across all profiles. Peaks reveal the most common water temperatures.">
                  <Plot
                    data={[{ type: 'histogram', x: temps, nbinsx: 30, marker: { color: '#f97316', line: { color: '#fdba74', width: 0.5 } } } as any]}
                    layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Temperature (\u00B0C)', gridcolor: GRID }, yaxis: { title: 'Count', gridcolor: GRID } }}
                    style={{ width: '100%', height: 260 }} config={PLOTLY_CFG}
                  />
                </ChartCard>
                {tempDepthPairs.t.length > 0 && (
                  <ChartCard title="Temperature vs Depth Profile" description="How temperature changes with ocean depth. The surface is warm; deeper layers are cold.">
                    <Plot
                      data={[{ x: tempDepthPairs.t, y: tempDepthPairs.d, mode: 'markers', type: 'scatter', marker: { color: tempDepthPairs.t, colorscale: 'YlOrRd', size: 3, opacity: 0.6, showscale: true, colorbar: { title: '\u00B0C', thickness: 10 } } } as any]}
                      layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Temperature (\u00B0C)', gridcolor: GRID }, yaxis: { title: 'Depth (m)', gridcolor: GRID, autorange: 'reversed' as const } }}
                      style={{ width: '100%', height: 260 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
                {tempTimePairs.ts.length > 10 && (
                  <ChartCard title="Temperature Time Series" description="Temperature measurements over time. Trends reveal warming, cooling, or seasonal cycles.">
                    <Plot
                      data={[{ x: tempTimePairs.ts, y: tempTimePairs.t, mode: 'markers', type: 'scatter', marker: { color: '#f97316', size: 3, opacity: 0.5 } } as any]}
                      layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Date', gridcolor: GRID, type: 'date' as const }, yaxis: { title: 'Temperature (\u00B0C)', gridcolor: GRID } }}
                      style={{ width: '100%', height: 260 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
                {tempTimePairs.ts.length > 20 && tempDepthPairs.t.length > 20 && (
                  <ChartCard title="Temperature Heatmap (Depth × Time)" description="A 2D view of how temperature varies across depth and time simultaneously.">
                    <Plot
                      data={[{
                        type: 'histogram2d',
                        x: (() => { if (!data) return []; const out: string[] = []; for (let i = 0; i < data.count; i++) { if (data.timestamp[i] && data.depth[i] != null && data.temperature[i] != null) out.push(data.timestamp[i]!); } return out; })(),
                        y: (() => { if (!data) return []; const out: number[] = []; for (let i = 0; i < data.count; i++) { if (data.timestamp[i] && data.depth[i] != null && data.temperature[i] != null) out.push(data.depth[i]!); } return out; })(),
                        z: (() => { if (!data) return []; const out: number[] = []; for (let i = 0; i < data.count; i++) { if (data.timestamp[i] && data.depth[i] != null && data.temperature[i] != null) out.push(data.temperature[i]!); } return out; })(),
                        histfunc: 'avg' as const,
                        colorscale: 'YlOrRd',
                        colorbar: { title: '\u00B0C', thickness: 10 },
                      } as any]}
                      layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Date', gridcolor: GRID, type: 'date' as const }, yaxis: { title: 'Depth (m)', gridcolor: GRID, autorange: 'reversed' as const } }}
                      style={{ width: '100%', height: 280 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
              </div>
            </Section>

            {/* \u2501\u2501\u2501 2. SALINITY ANALYSIS \u2501\u2501\u2501 */}
            <Section title="Salinity Analysis" icon={<Droplets className="w-4 h-4" />} color="bg-sky-500/15 text-sky-400" count={4}>
              <InsightBox insights={data ? salInsights(data) : []} />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <ChartCard title="Salinity Distribution" description="Frequency of salinity values. Most ocean water is 34\u201336 PSU. Outliers indicate freshwater mixing.">
                  <Plot
                    data={[{ type: 'histogram', x: sals, nbinsx: 30, marker: { color: '#0ea5e9', line: { color: '#7dd3fc', width: 0.5 } } } as any]}
                    layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Salinity (PSU)', gridcolor: GRID }, yaxis: { title: 'Count', gridcolor: GRID } }}
                    style={{ width: '100%', height: 260 }} config={PLOTLY_CFG}
                  />
                </ChartCard>
                {salDepthPairs.s.length > 0 && (
                  <ChartCard title="Salinity vs Depth Profile" description="How salinity changes with depth. Surface salinity varies due to evaporation and rain; deep values are stable.">
                    <Plot
                      data={[{ x: salDepthPairs.s, y: salDepthPairs.d, mode: 'markers', type: 'scatter', marker: { color: salDepthPairs.s, colorscale: 'Blues', size: 3, opacity: 0.6, reversescale: true, showscale: true, colorbar: { title: 'PSU', thickness: 10 } } } as any]}
                      layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Salinity (PSU)', gridcolor: GRID }, yaxis: { title: 'Depth (m)', gridcolor: GRID, autorange: 'reversed' as const } }}
                      style={{ width: '100%', height: 260 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
                {sals.length > 0 && data?.unique_floats && data.unique_floats.length > 1 && (
                  <ChartCard title="Salinity Variability by Float" description="Comparing salinity distributions across different ARGO floats to identify regional differences.">
                    <Plot
                      data={data.unique_floats.slice(0, 8).map((fid, idx) => {
                        const fSals: number[] = [];
                        for (let i = 0; i < data.count; i++) { if (data.float_id[i] === fid && data.salinity[i] != null) fSals.push(data.salinity[i]!); }
                        return { type: 'box' as const, y: fSals, name: fid.length > 12 ? fid.slice(-8) : fid, marker: { color: ['#0ea5e9', '#06b6d4', '#14b8a6', '#8b5cf6', '#f59e0b', '#ef4444', '#ec4899', '#84cc16'][idx % 8] } };
                      })}
                      layout={{ ...PLOTLY_LAYOUT_BASE, yaxis: { title: 'Salinity (PSU)', gridcolor: GRID }, showlegend: false }}
                      style={{ width: '100%', height: 260 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
                {sals.length > 10 && data?.sal_stats && (
                  <ChartCard title="Salinity Anomaly" description="Deviation from the mean salinity. Positive = saltier than average, Negative = fresher than average.">
                    <Plot
                      data={[{
                        type: 'histogram', x: sals.map(s => s - data.sal_stats!.mean), nbinsx: 30,
                        marker: { color: sals.map(s => s - data.sal_stats!.mean > 0 ? '#f97316' : '#0ea5e9') },
                      } as any]}
                      layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Salinity Anomaly (PSU)', gridcolor: GRID }, yaxis: { title: 'Count', gridcolor: GRID }, shapes: [{ type: 'line', x0: 0, x1: 0, y0: 0, y1: 1, yref: 'paper', line: { color: '#94a3b8', width: 1, dash: 'dot' } }] }}
                      style={{ width: '100%', height: 260 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
              </div>
            </Section>

            {/* \u2501\u2501\u2501 3. OCEAN STRUCTURE \u2501\u2501\u2501 */}
            <Section title="Ocean Structure Analysis" icon={<Waves className="w-4 h-4" />} color="bg-emerald-500/15 text-emerald-400" count={3}>
              <InsightBox insights={data ? oceanInsights(data) : []} />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {tsPairs.t.length > 0 && (
                  <ChartCard title="Temperature–Salinity (T–S) Diagram" description="The classic oceanographic tool. Each point is one measurement colored by depth. Clusters reveal distinct water masses.">
                    <Plot
                      data={[{
                        x: tsPairs.s, y: tsPairs.t, mode: 'markers', type: 'scatter',
                        marker: { color: tsPairs.d, colorscale: 'Viridis', size: 4, opacity: 0.65, showscale: true, colorbar: { title: 'Depth (m)', thickness: 10 } },
                        text: tsPairs.t.map((t, i) => `T: ${t.toFixed(1)}\u00B0C<br>S: ${tsPairs.s[i].toFixed(2)} PSU<br>D: ${tsPairs.d[i].toFixed(0)} m`),
                        hovertemplate: '%{text}<extra></extra>',
                      } as any]}
                      layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Salinity (PSU)', gridcolor: GRID, zeroline: false }, yaxis: { title: 'Temperature (\u00B0C)', gridcolor: GRID, zeroline: false } }}
                      style={{ width: '100%', height: 320 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
                {densityData && (
                  <ChartCard title="Density Estimation (σ_t)" description="Estimated seawater density from T and S using UNESCO EOS-80. Color shows sigma-t values related to ocean stratification.">
                    <Plot
                      data={[{
                        x: densityData.s, y: densityData.t, mode: 'markers', type: 'scatter',
                        marker: { color: densityData.sigma, colorscale: 'Portland', size: 4, opacity: 0.65, showscale: true, colorbar: { title: '\u03C3_t', thickness: 10 } },
                      } as any]}
                      layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Salinity (PSU)', gridcolor: GRID }, yaxis: { title: 'Temperature (\u00B0C)', gridcolor: GRID } }}
                      style={{ width: '100%', height: 320 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
                {densityData && densityData.sigma.length > 20 && (
                  <ChartCard title="Water Mass Classification" description="Data grouped by density ranges: Surface, Intermediate, Deep, and Bottom water. Each band corresponds to a different water mass.">
                    <Plot
                      data={(() => {
                        const classes = [
                          { name: 'Surface (\u03C3<25)', range: [-Infinity, 25], color: '#ef4444' },
                          { name: 'Intermediate (25\u201327)', range: [25, 27], color: '#f59e0b' },
                          { name: 'Deep (27\u201328)', range: [27, 28], color: '#06b6d4' },
                          { name: 'Bottom (\u03C3>28)', range: [28, Infinity], color: '#3b82f6' },
                        ];
                        return classes.map(c => {
                          const idxs = densityData!.sigma.map((s, i) => (s >= c.range[0] && s < c.range[1]) ? i : -1).filter(i => i >= 0);
                          return {
                            x: idxs.map(i => densityData!.s[i]),
                            y: idxs.map(i => densityData!.t[i]),
                            mode: 'markers', type: 'scatter', name: c.name,
                            marker: { color: c.color, size: 4, opacity: 0.7 },
                          } as any;
                        });
                      })()}
                      layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Salinity (PSU)', gridcolor: GRID }, yaxis: { title: 'Temperature (\u00B0C)', gridcolor: GRID }, legend: { font: { size: 10 }, bgcolor: 'rgba(0,0,0,0)' } }}
                      style={{ width: '100%', height: 320 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
              </div>
            </Section>

            {/* \u2501\u2501\u2501 4. DEPTH ANALYSIS \u2501\u2501\u2501 */}
            <Section title="Depth Analysis" icon={<Activity className="w-4 h-4" />} color="bg-purple-500/15 text-purple-400" count={3}>
              <InsightBox insights={data ? depthInsights(data) : []} />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <ChartCard title="Depth Distribution" description="How measurement depths are distributed. Peaks show where instruments sample most.">
                  <Plot
                    data={[{ type: 'histogram', x: depths, nbinsx: 30, marker: { color: '#a855f7', line: { color: '#c084fc', width: 0.5 } } } as any]}
                    layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Depth (m)', gridcolor: GRID }, yaxis: { title: 'Count', gridcolor: GRID } }}
                    style={{ width: '100%', height: 260 }} config={PLOTLY_CFG}
                  />
                </ChartCard>
                {tempDepthPairs.t.length > 0 && salDepthPairs.s.length > 0 && (
                  <ChartCard title="Temperature & Salinity vs Depth" description="Both variables plotted against depth to visualize the thermocline and halocline simultaneously.">
                    <Plot
                      data={[
                        { x: tempDepthPairs.t, y: tempDepthPairs.d, mode: 'markers', type: 'scatter', name: 'Temp (\u00B0C)', marker: { color: '#f97316', size: 3, opacity: 0.4 }, xaxis: 'x' } as any,
                        { x: salDepthPairs.s, y: salDepthPairs.d, mode: 'markers', type: 'scatter', name: 'Sal (PSU)', marker: { color: '#0ea5e9', size: 3, opacity: 0.4 }, xaxis: 'x2' } as any,
                      ]}
                      layout={{
                        ...PLOTLY_LAYOUT_BASE,
                        xaxis: { title: 'Temperature (\u00B0C)', gridcolor: GRID, side: 'bottom' as const, titlefont: { color: '#f97316' } as any },
                        xaxis2: { title: 'Salinity (PSU)', gridcolor: GRID, side: 'top' as const, overlaying: 'x' as const, titlefont: { color: '#0ea5e9' } as any },
                        yaxis: { title: 'Depth (m)', gridcolor: GRID, autorange: 'reversed' as const },
                        legend: { font: { size: 10 }, bgcolor: 'rgba(0,0,0,0)', x: 1, xanchor: 'right' as const },
                      }}
                      style={{ width: '100%', height: 300 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
                {thermoclineData && (
                  <ChartCard title="Thermocline Detection" description="The temperature gradient (°C per 100m) reveals the thermocline — the layer where temperature drops most rapidly.">
                    <Plot
                      data={[
                        { x: thermoclineData.buckets.map(b => b.temp), y: thermoclineData.buckets.map(b => b.depth), mode: 'lines+markers', type: 'scatter', name: 'Avg Temp', marker: { color: '#f97316', size: 4 }, line: { color: '#f97316', width: 2 } } as any,
                        { x: thermoclineData.gradients.map(g => g.gradient), y: thermoclineData.gradients.map(g => g.depth), mode: 'lines+markers', type: 'scatter', name: 'Gradient', marker: { color: '#a855f7', size: 4 }, line: { color: '#a855f7', width: 2 }, xaxis: 'x2' } as any,
                      ]}
                      layout={{
                        ...PLOTLY_LAYOUT_BASE,
                        xaxis: { title: 'Temperature (\u00B0C)', gridcolor: GRID, titlefont: { color: '#f97316' } as any },
                        xaxis2: { title: 'Gradient (\u00B0C/100m)', overlaying: 'x' as const, side: 'top' as const, gridcolor: GRID, titlefont: { color: '#a855f7' } as any },
                        yaxis: { title: 'Depth (m)', gridcolor: GRID, autorange: 'reversed' as const },
                        legend: { font: { size: 10 }, bgcolor: 'rgba(0,0,0,0)' },
                      }}
                      style={{ width: '100%', height: 300 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
              </div>
            </Section>

            {/* \u2501\u2501\u2501 5. TEMPORAL ANALYSIS \u2501\u2501\u2501 */}
            <Section title="Temporal Analysis" icon={<Clock className="w-4 h-4" />} color="bg-amber-500/15 text-amber-400" count={3}>
              <InsightBox insights={data ? temporalInsights(data) : []} />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {tempTimePairs.ts.length > 10 && (
                  <ChartCard title="Temperature Trend Over Time" description="Temperature measurements plotted chronologically. A moving average line reveals the underlying trend.">
                    <Plot
                      data={[
                        { x: tempTimePairs.ts, y: tempTimePairs.t, mode: 'markers', type: 'scatter', name: 'Raw', marker: { color: '#f97316', size: 3, opacity: 0.3 } } as any,
                        ...(() => {
                          const sorted = tempTimePairs.ts.map((ts, i) => ({ ts, t: tempTimePairs.t[i] })).sort((a, b) => a.ts.localeCompare(b.ts));
                          const w = Math.max(5, Math.floor(sorted.length / 20));
                          const maTs: string[] = [], maT: number[] = [];
                          for (let i = w; i < sorted.length; i++) {
                            maTs.push(sorted[i].ts);
                            maT.push(sorted.slice(i - w, i).reduce((a, b) => a + b.t, 0) / w);
                          }
                          return [{ x: maTs, y: maT, mode: 'lines', type: 'scatter', name: 'Moving Avg', line: { color: '#fbbf24', width: 2 } } as any];
                        })(),
                      ]}
                      layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Date', gridcolor: GRID, type: 'date' as const }, yaxis: { title: 'Temperature (\u00B0C)', gridcolor: GRID }, legend: { font: { size: 10 }, bgcolor: 'rgba(0,0,0,0)' } }}
                      style={{ width: '100%', height: 260 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
                {salTimePairs.ts.length > 10 && (
                  <ChartCard title="Salinity Trend Over Time" description="Salinity measurements over time. Variations can indicate changes in evaporation, precipitation, or ocean circulation.">
                    <Plot
                      data={[
                        { x: salTimePairs.ts, y: salTimePairs.s, mode: 'markers', type: 'scatter', name: 'Raw', marker: { color: '#0ea5e9', size: 3, opacity: 0.3 } } as any,
                        ...(() => {
                          const sorted = salTimePairs.ts.map((ts, i) => ({ ts, s: salTimePairs.s[i] })).sort((a, b) => a.ts.localeCompare(b.ts));
                          const w = Math.max(5, Math.floor(sorted.length / 20));
                          const maTs: string[] = [], maS: number[] = [];
                          for (let i = w; i < sorted.length; i++) {
                            maTs.push(sorted[i].ts);
                            maS.push(sorted.slice(i - w, i).reduce((a, b) => a + b.s, 0) / w);
                          }
                          return [{ x: maTs, y: maS, mode: 'lines', type: 'scatter', name: 'Moving Avg', line: { color: '#38bdf8', width: 2 } } as any];
                        })(),
                      ]}
                      layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Date', gridcolor: GRID, type: 'date' as const }, yaxis: { title: 'Salinity (PSU)', gridcolor: GRID }, legend: { font: { size: 10 }, bgcolor: 'rgba(0,0,0,0)' } }}
                      style={{ width: '100%', height: 260 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
                {seasonalData && Object.values(seasonalData).some(v => v.length > 0) && (
                  <ChartCard title="Seasonal Temperature Patterns" description="Temperature distributions grouped by meteorological season. Reveals seasonal warming and cooling cycles.">
                    <Plot
                      data={Object.entries(seasonalData).map(([name, vals], idx) => ({
                        type: 'box' as const, y: vals, name,
                        marker: { color: ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444'][idx] },
                      }))}
                      layout={{ ...PLOTLY_LAYOUT_BASE, yaxis: { title: 'Temperature (\u00B0C)', gridcolor: GRID }, showlegend: false }}
                      style={{ width: '100%', height: 280 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
              </div>
            </Section>

            {/* \u2501\u2501\u2501 6. GEOGRAPHIC ANALYSIS \u2501\u2501\u2501 */}
            <Section title="Geographic Analysis" icon={<MapPin className="w-4 h-4" />} color="bg-rose-500/15 text-rose-400" count={3}>
              <InsightBox insights={data ? geoInsights(data) : []} />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <ChartCard title="Float Locations" description="Geographic positions of all measurements, colored by ARGO float. Shows how each float drifts with ocean currents.">
                  <Plot
                    data={(() => {
                      const floats = data?.unique_floats || [];
                      const colors = ['#ef4444', '#f59e0b', '#22c55e', '#06b6d4', '#8b5cf6', '#ec4899', '#3b82f6', '#14b8a6'];
                      return floats.slice(0, 8).map((fid, idx) => {
                        const fLats: number[] = [], fLons: number[] = [];
                        for (let i = 0; i < data!.count; i++) { if (data!.float_id[i] === fid) { fLats.push(data!.latitude[i]); fLons.push(data!.longitude[i]); } }
                        return {
                          type: 'scattergeo' as const, lat: fLats, lon: fLons, mode: 'markers',
                          name: fid.length > 12 ? fid.slice(-8) : fid,
                          marker: { color: colors[idx % 8], size: 5, opacity: 0.7 },
                        };
                      });
                    })()}
                    layout={{
                      ...PLOTLY_LAYOUT_BASE,
                      geo: {
                        bgcolor: 'rgba(15,23,42,0.4)',
                        showland: true, landcolor: '#1e293b',
                        showocean: true, oceancolor: '#0f172a',
                        showcoastlines: true, coastlinecolor: '#334155',
                        showframe: false,
                        projection: { type: 'natural earth' as const },
                      } as any,
                      legend: { font: { size: 9, color: '#94a3b8' }, bgcolor: 'rgba(0,0,0,0)' },
                      margin: { t: 8, r: 8, b: 8, l: 8 },
                    }}
                    style={{ width: '100%', height: 300 }} config={PLOTLY_CFG}
                  />
                </ChartCard>
                {temps.length > 0 && (
                  <ChartCard title="Temperature Geographic Map" description="Temperature mapped at measurement locations. Red = warm surface waters, Blue = cold deep or polar waters.">
                    <Plot
                      data={[{
                        type: 'scattergeo', lat: lats, lon: lons, mode: 'markers',
                        marker: { color: temps.length === lats.length ? temps : lats.map(() => 0), colorscale: 'RdBu', reversescale: true, size: 5, opacity: 0.65, showscale: true, colorbar: { title: '\u00B0C', thickness: 10 } },
                        text: lats.map((lat, i) => `${lat.toFixed(1)}\u00B0, ${lons[i].toFixed(1)}\u00B0`),
                      } as any]}
                      layout={{
                        ...PLOTLY_LAYOUT_BASE,
                        geo: {
                          bgcolor: 'rgba(15,23,42,0.4)',
                          showland: true, landcolor: '#1e293b',
                          showocean: true, oceancolor: '#0f172a',
                          showcoastlines: true, coastlinecolor: '#334155',
                          showframe: false,
                          projection: { type: 'natural earth' as const },
                        } as any,
                        margin: { t: 8, r: 8, b: 8, l: 8 },
                      }}
                      style={{ width: '100%', height: 300 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
                {sals.length > 0 && (
                  <ChartCard title="Salinity Geographic Map" description="Salinity at each measurement location. Variations reflect freshwater input, evaporation patterns, and water mass boundaries.">
                    <Plot
                      data={[{
                        type: 'scattergeo', lat: lats, lon: lons, mode: 'markers',
                        marker: { color: sals.length === lats.length ? sals : lats.map(() => 35), colorscale: 'Blues', size: 5, opacity: 0.65, showscale: true, colorbar: { title: 'PSU', thickness: 10 } },
                      } as any]}
                      layout={{
                        ...PLOTLY_LAYOUT_BASE,
                        geo: {
                          bgcolor: 'rgba(15,23,42,0.4)',
                          showland: true, landcolor: '#1e293b',
                          showocean: true, oceancolor: '#0f172a',
                          showcoastlines: true, coastlinecolor: '#334155',
                          showframe: false,
                          projection: { type: 'natural earth' as const },
                        } as any,
                        margin: { t: 8, r: 8, b: 8, l: 8 },
                      }}
                      style={{ width: '100%', height: 300 }} config={PLOTLY_CFG}
                    />
                  </ChartCard>
                )}
              </div>
            </Section>

          </div>
        ) : !loading ? (
          <div className="text-center py-16 text-slate-500">
            <Globe className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm">No data available for this region. Try selecting a different area.</p>
          </div>
        ) : null}
      </div>
    </div>
  );
};

/* Summary stat card */
const SummaryCard: React.FC<{
  icon: React.ReactNode; color: string; bg: string;
  label: string; value: string; sub?: string;
}> = ({ icon, color, bg, label, value, sub }) => (
  <div className="bg-slate-800/50 border border-white/5 rounded-xl px-3.5 py-3">
    <div className="flex items-center gap-2 mb-1.5">
      <span className={`${bg} ${color} p-1.5 rounded-lg`}>{icon}</span>
      <span className="text-[11px] text-slate-400 font-medium">{label}</span>
    </div>
    <p className="text-lg font-bold tracking-tight">{value}</p>
    {sub && <p className="text-[10px] text-slate-500 mt-0.5">{sub}</p>}
  </div>
);
