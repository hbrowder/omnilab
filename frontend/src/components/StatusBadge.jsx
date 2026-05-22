import React, { useState, useEffect } from 'react'

// Status Badge - floating widget that polls /api/health/metrics
// Color states:
//   green  = all OK (CPU < 80%, RAM < 85%)
//   yellow = warning (CPU/RAM elevated)
//   red    = backend unreachable or critical (CPU > 95% or RAM > 95%)
//   gray   = loading / unknown

export default function StatusBadge() {
  const [state, setState] = useState({ color: 'gray', label: 'Loading...', detail: null })
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function check() {
      try {
        const r = await fetch('/api/health/metrics')
        if (!r.ok) throw new Error('HTTP ' + r.status)
        const m = await r.json()
        if (cancelled) return

        const cpu = m.cpu_percent ?? 0
        const ram = m.memory_percent ?? 0
        const disk = m.disk_percent ?? 0

        let color = 'green'
        let label = 'Healthy'
        if (cpu > 95 || ram > 95 || disk > 95) {
          color = 'red'
          label = 'Critical'
        } else if (cpu > 80 || ram > 85 || disk > 90) {
          color = 'yellow'
          label = 'Warning'
        }

        setState({ color, label, detail: { cpu, ram, disk } })
      } catch (e) {
        if (!cancelled) {
          setState({ color: 'red', label: 'Offline', detail: { error: String(e.message || e) } })
        }
      }
    }

    check()
    const interval = setInterval(check, 10000) // poll every 10 seconds
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  const colorMap = {
    green:  { dot: '#3fb950', bg: '#0d2818', border: '#1f6b3a', text: '#7ee79a' },
    yellow: { dot: '#d29922', bg: '#2b2415', border: '#6b5c1f', text: '#f1cb59' },
    red:    { dot: '#f85149', bg: '#2b1417', border: '#6b1f24', text: '#ff8a85' },
    gray:   { dot: '#6e7681', bg: '#161b22', border: '#21262d', text: '#8b949e' },
  }
  const c = colorMap[state.color] || colorMap.gray

  return (
    <div
      onClick={() => setExpanded(!expanded)}
      style={{
        position: 'fixed',
        bottom: 16,
        right: 16,
        background: c.bg,
        border: '1px solid ' + c.border,
        borderRadius: expanded ? 8 : 999,
        padding: expanded ? '10px 14px' : '6px 12px',
        fontSize: 12,
        color: c.text,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
        zIndex: 9999,
        userSelect: 'none',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        transition: 'all 0.2s ease',
      }}
      title="Click to toggle details"
    >
      <span style={{
        display: 'inline-block',
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: c.dot,
        boxShadow: '0 0 6px ' + c.dot,
      }} />
      <span style={{ fontWeight: 600 }}>{state.label}</span>
      {expanded && state.detail && (
        <div style={{ marginLeft: 8, fontSize: 11, opacity: 0.85 }}>
          {state.detail.error ? (
            <span>{state.detail.error}</span>
          ) : (
            <span>
              CPU {state.detail.cpu?.toFixed?.(1) ?? state.detail.cpu}%
              {' · '}
              RAM {state.detail.ram?.toFixed?.(1) ?? state.detail.ram}%
              {' · '}
              Disk {state.detail.disk?.toFixed?.(1) ?? state.detail.disk}%
            </span>
          )}
        </div>
      )}
    </div>
  )
}
