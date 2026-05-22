import React, { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'

// ─── Palette (matches OmniLab dark theme) ────────────────────────────────────
const C = {
  bg:       '#0d1117',
  card:     '#161b22',
  border:   '#21262d',
  text:     '#e6edf3',
  dim:      '#8b949e',
  accent:   '#58a6ff',
  green:    '#3fb950',
  yellow:   '#d29922',
  red:      '#f85149',
  purple:   '#bc8cff',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const fmt = {
  bytes: b => {
    if (b >= 1e9) return (b / 1e9).toFixed(1) + ' GB'
    if (b >= 1e6) return (b / 1e6).toFixed(1) + ' MB'
    return (b / 1e3).toFixed(1) + ' KB'
  },
  uptime: s => {
    const d = Math.floor(s / 86400)
    const h = Math.floor((s % 86400) / 3600)
    const m = Math.floor((s % 3600) / 60)
    if (d > 0) return `${d}d ${h}h ${m}m`
    if (h > 0) return `${h}h ${m}m`
    return `${m}m`
  },
  pct: n => (n ?? 0).toFixed(1) + '%',
}

function statusColor(pct, warn = 70, crit = 85) {
  if (pct >= crit) return C.red
  if (pct >= warn) return C.yellow
  return C.green
}

// ─── Sparkline ────────────────────────────────────────────────────────────────
function Sparkline({ data, color, height = 32 }) {
  const w = 80
  if (!data || data.length < 2) return <svg width={w} height={height} />
  const max = Math.max(...data, 1)
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w
    const y = height - (v / max) * height
    return `${x},${y}`
  }).join(' ')
  return (
    <svg width={w} height={height} style={{ overflow: 'visible' }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  )
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────
function KpiCard({ label, value, unit, pct, history, warn, crit }) {
  const col = pct != null ? statusColor(pct, warn, crit) : C.accent
  return (
    <div style={{
      background: C.card, border: `1px solid ${C.border}`, borderRadius: 10,
      padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      <div style={{ fontSize: 12, color: C.dim, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
        <div>
          <span style={{ fontSize: 28, fontWeight: 700, color: col, fontFamily: 'monospace' }}>{value}</span>
          {unit && <span style={{ fontSize: 13, color: C.dim, marginLeft: 4 }}>{unit}</span>}
        </div>
        {history && <Sparkline data={history} color={col} />}
      </div>
      {pct != null && (
        <div style={{ height: 4, background: C.border, borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ width: `${Math.min(pct, 100)}%`, height: '100%', background: col, borderRadius: 2, transition: 'width .3s' }} />
        </div>
      )}
    </div>
  )
}

// ─── Section wrapper ──────────────────────────────────────────────────────────
function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{
        fontSize: 11, fontWeight: 700, color: C.dim, textTransform: 'uppercase',
        letterSpacing: '0.1em', marginBottom: 12, paddingBottom: 8,
        borderBottom: `1px solid ${C.border}`
      }}>{title}</div>
      {children}
    </div>
  )
}

// ─── Stat row ─────────────────────────────────────────────────────────────────
function StatRow({ label, value, color }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: `1px solid ${C.border}` }}>
      <span style={{ fontSize: 13, color: C.dim }}>{label}</span>
      <span style={{ fontSize: 13, color: color || C.text, fontFamily: 'monospace' }}>{value ?? '—'}</span>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function HealthDashboard() {
  const POLL = 5000
  const MAX_HISTORY = 60

  const [metrics, setMetrics]   = useState(null)
  const [docker,  setDocker]    = useState(null)
  const [network, setNetwork]   = useState(null)
  const [labs,    setLabs]      = useState(null)
  const [error,   setError]     = useState(null)
  const [lastTs,  setLastTs]    = useState(null)
  const [loading, setLoading]   = useState(true)

  const cpuHist = useRef([])
  const ramHist = useRef([])

  const fetch = useCallback(async (isManual = false) => {
    if (isManual) setLoading(true)
    try {
      const [m, d, n, l] = await Promise.all([
        axios.get('/api/health/metrics'),
        axios.get('/api/health/docker'),
        axios.get('/api/health/network'),
        axios.get('/api/health/lab-stats'),
      ])
      setMetrics(m.data)
      setDocker(d.data)
      setNetwork(n.data)
      setLabs(l.data)
      setError(null)
      setLastTs(new Date())

      cpuHist.current = [...cpuHist.current, m.data.cpu ?? 0].slice(-MAX_HISTORY)
      ramHist.current = [...ramHist.current, m.data.ram ?? 0].slice(-MAX_HISTORY)
    } catch (e) {
      setError('Failed to reach backend: ' + (e.message || String(e)))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch()
    const id = setInterval(() => fetch(), POLL)
    // Pause polling when tab is hidden (saves resources)
    const onVis = () => { if (!document.hidden) fetch() }
    document.addEventListener('visibilitychange', onVis)
    return () => { clearInterval(id); document.removeEventListener('visibilitychange', onVis) }
  }, [fetch])

  // ── Render ──
  const s = { padding: '24px 28px', minHeight: '100%', background: C.bg, color: C.text, fontFamily: 'system-ui,sans-serif' }

  return (
    <div style={s}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: C.text }}>System Health</h1>
          <div style={{ fontSize: 13, color: C.dim, marginTop: 4 }}>
            {lastTs ? `Last updated ${lastTs.toLocaleTimeString()}` : 'Loading…'}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {error && (
            <span style={{ fontSize: 12, color: C.red, background: '#2d1117', border: `1px solid ${C.red}`, borderRadius: 6, padding: '4px 10px' }}>
              ⚠ {error}
            </span>
          )}
          <button
            onClick={() => fetch(true)}
            disabled={loading}
            style={{
              background: loading ? C.border : C.card, border: `1px solid ${C.border}`,
              color: loading ? C.dim : C.accent, borderRadius: 8, padding: '7px 16px',
              fontSize: 13, cursor: loading ? 'wait' : 'pointer', fontWeight: 600,
            }}>
            {loading ? 'Refreshing…' : '↺ Refresh'}
          </button>
        </div>
      </div>

      {/* KPI row */}
      <Section title="System">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 0 }}>
          <KpiCard
            label="CPU"
            value={metrics ? fmt.pct(metrics.cpu) : '—'}
            pct={metrics?.cpu}
            history={cpuHist.current}
            warn={70} crit={90}
          />
          <KpiCard
            label="Memory"
            value={metrics ? fmt.pct(metrics.ram) : '—'}
            pct={metrics?.ram}
            history={ramHist.current}
            warn={75} crit={92}
          />
          <KpiCard
            label="Disk"
            value={metrics ? fmt.pct(metrics.disk) : '—'}
            pct={metrics?.disk}
            warn={80} crit={95}
          />
          <KpiCard
            label="Uptime"
            value={metrics ? fmt.uptime(metrics.uptime) : '—'}
          />
        </div>
      </Section>

      {/* Two-column detail grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>

        {/* Left column */}
        <div>
          <Section title="Docker">
            <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: '4px 16px' }}>
              <StatRow label="Containers running" value={docker ? `${docker.containers_running} / ${docker.containers_total}` : '—'} color={docker?.containers_running > 0 ? C.green : C.dim} />
              <StatRow label="Images" value={docker?.images_count} />
              <StatRow label="Storage used" value={docker ? fmt.bytes(docker.storage_bytes) : '—'} />
              <StatRow label="Active pulls" value={docker ? (docker.pulling?.length || 0) : '—'} />
            </div>
          </Section>

          <Section title="Network">
            <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: '4px 16px' }}>
              <StatRow label="OVS bridges" value={network?.bridges?.length ?? '—'} />
              <StatRow label="Interfaces up" value={network?.interfaces_up} color={C.green} />
              <StatRow label="Interfaces down" value={network?.interfaces_down} color={network?.interfaces_down > 0 ? C.red : C.dim} />
              <StatRow label="Active links" value={network?.active_links} />
            </div>
          </Section>

          <Section title="Backend Process">
            <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: '4px 16px' }}>
              <StatRow label="Version" value={metrics?.version} color={C.accent} />
              <StatRow label="Python" value={metrics?.python_version} />
              <StatRow label="Process RAM" value={metrics ? fmt.bytes(metrics.process_ram) : '—'} />
              <StatRow label="Process CPU" value={metrics ? fmt.pct(metrics.process_cpu) : '—'} />
              <StatRow label="Threads" value={metrics?.threads} />
            </div>
          </Section>
        </div>

        {/* Right column */}
        <div>
          <Section title="Labs">
            <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: '4px 16px' }}>
              <StatRow label="Total labs" value={labs?.total_labs} />
              <StatRow label="Active labs" value={labs?.active_labs} color={labs?.active_labs > 0 ? C.green : C.dim} />
              <StatRow label="Total nodes" value={labs?.total_nodes} />
              <StatRow label="Running nodes" value={labs?.running_nodes} color={labs?.running_nodes > 0 ? C.green : C.dim} />
              <StatRow label="Stopped nodes" value={labs?.stopped_nodes} color={C.dim} />
            </div>
            {labs?.by_category && Object.keys(labs.by_category).length > 0 && (
              <div style={{ marginTop: 10, background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: '4px 16px' }}>
                {Object.entries(labs.by_category).map(([cat, count]) => (
                  <StatRow key={cat} label={cat.charAt(0).toUpperCase() + cat.slice(1)} value={count} />
                ))}
              </div>
            )}
          </Section>

          <Section title="API">
            <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: '4px 16px' }}>
              <StatRow
                label="Backend status"
                value={metrics?.api_healthy ? '● Healthy' : '● Unreachable'}
                color={metrics?.api_healthy ? C.green : C.red}
              />
              <StatRow label="WebSocket connections" value={metrics?.ws_connections} />
              <StatRow label="Requests / min" value={metrics?.requests_per_min} />
              <StatRow label="Avg latency" value={metrics ? `${metrics.avg_latency_ms} ms` : '—'} />
              <StatRow
                label="Errors last hour"
                value={metrics?.errors_last_hour}
                color={metrics?.errors_last_hour > 0 ? C.red : C.dim}
              />
            </div>
          </Section>
        </div>

      </div>
    </div>
  )
}
