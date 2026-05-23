import React, { useState, useEffect, useRef } from 'react'
import { updateNodeConfig, getNodeWebInfo, provisionWsUrl } from '../utils/api'

/**
 * NodePanel — right-rail inspector for a selected node.
 *
 * CRE-39 phase 4 additions:
 *  - Pull-progress bar: subscribes to /api/nodes/{id}/provision-ws and surfaces
 *    docker pull events ({status, progressDetail.current/total, id}) as a
 *    per-layer progress strip while a docker node is starting.
 *  - "Open Web UI" button: probes /api/labs/{labId}/nodes/{id}/web-info on
 *    mount; if the node exposes a web port, renders a button that opens the
 *    backend reverse proxy at /labs/{labId}/nodes/{id}/web/ in a new tab.
 *
 * The pull-progress UI auto-clears when the node finishes provisioning (no
 * new events for 5 seconds and the layer set is empty / all complete). The
 * WebSocket itself stays open for the lifetime of the panel — cheap, and
 * means re-starting a node mid-session lights the bar up again without re-
 * mounting.
 */

export default function NodePanel({ node, labId, onDelete, onClose, onStart, onStop, onOpenConsole, onSaved }) {
  const data = node.data || {}
  const [config, setConfig] = useState('')
  const [name, setName] = useState(data.label || '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [activeTab, setActiveTab] = useState('info')

  // CRE-39: web-info (Open Web UI button) ----------------------------------
  const [webInfo, setWebInfo] = useState(null)

  // CRE-39: provision-ws (docker pull progress) ----------------------------
  // Map: layer_id -> { status, current, total, complete }
  // We render this as a vertical strip of mini progress bars during a pull.
  const [pullLayers, setPullLayers] = useState({})
  const [pullActive, setPullActive] = useState(false)
  const wsRef = useRef(null)
  const idleTimerRef = useRef(null)
  const isDocker = (data.type || '').toLowerCase() === 'docker'

  useEffect(() => {
    setConfig(data.config || '')
    setName(data.label || '')
    setSaved(false)
    setPullLayers({})
    setPullActive(false)
  }, [node.id])

  // ----- web-info probe on mount + when node changes ------------------------
  useEffect(() => {
    if (!isDocker || !labId || !node.id) {
      setWebInfo(null)
      return
    }
    let cancelled = false
    getNodeWebInfo(labId, node.id)
      .then(r => { if (!cancelled) setWebInfo(r.data) })
      .catch(() => { if (!cancelled) setWebInfo(null) })
    return () => { cancelled = true }
  }, [isDocker, labId, node.id])

  // ----- provision-ws subscription -----------------------------------------
  useEffect(() => {
    if (!isDocker || !node.id) return
    const url = provisionWsUrl(node.id)
    let ws
    try {
      ws = new WebSocket(url)
    } catch (e) {
      // URL building issue — give up silently, the bar just won't show
      return
    }
    wsRef.current = ws

    const resetIdleTimer = () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current)
      idleTimerRef.current = setTimeout(() => {
        // 5s with no events == pull finished. Clear and reset.
        setPullActive(false)
        setPullLayers({})
      }, 5000)
    }

    ws.onmessage = (evt) => {
      let msg
      try { msg = JSON.parse(evt.data) } catch { return }
      if (msg.type === 'ping') return  // heartbeat
      if (msg.type !== 'pull') return

      const layerId = msg.id || '_global'
      const status = msg.status || ''
      const detail = msg.progressDetail || {}
      setPullActive(true)
      setPullLayers(prev => ({
        ...prev,
        [layerId]: {
          status,
          current: detail.current || 0,
          total: detail.total || 0,
          complete: /^(Pull complete|Already exists|Download complete)$/i.test(status),
        }
      }))
      resetIdleTimer()
    }

    ws.onclose = () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current)
    }

    return () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current)
      try { ws.close() } catch { /* noop */ }
    }
  }, [isDocker, node.id])

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      await updateNodeConfig(node.id, { name, config })
      setSaved(true)
      if (onSaved) onSaved(node.id, { name, config })
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      alert('Save failed: ' + (e.message || e))
    } finally {
      setSaving(false)
    }
  }

  const handleOpenWebUI = () => {
    if (!webInfo?.proxy_url) return
    window.open(webInfo.proxy_url, '_blank', 'noopener,noreferrer')
  }

  // ----- pull-progress render helpers --------------------------------------
  const layerEntries = Object.entries(pullLayers)
  const overallPct = (() => {
    if (!layerEntries.length) return 0
    const totals = layerEntries.reduce(
      (acc, [, l]) => {
        if (l.total > 0) {
          acc.current += l.current
          acc.total += l.total
        } else if (l.complete) {
          // Treat complete layers without size info as fully done.
          acc.current += 1
          acc.total += 1
        }
        return acc
      },
      { current: 0, total: 0 }
    )
    return totals.total > 0 ? Math.min(100, Math.round((totals.current / totals.total) * 100)) : 0
  })()

  return (
    <div style={{ width:300, background:'#161b22', borderLeft:'1px solid #21262d', padding:16, display:'flex', flexDirection:'column', gap:12, flexShrink:0, overflowY:'auto' }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <span style={{ fontSize:14, fontWeight:600, color:'#e6edf3' }}>Node Inspector</span>
        <button onClick={onClose} style={{ background:'none', border:'none', color:'#8b949e', cursor:'pointer', fontSize:18 }}>×</button>
      </div>

      <div style={{ background:'#21262d', borderRadius:8, padding:'12px 14px' }}>
        <div style={{ fontSize:18, marginBottom:6 }}>{data.type==='docker'?'🐳':'💻'}</div>
        <div style={{ fontSize:15, fontWeight:600, color:'#e6edf3', marginBottom:2 }}>{data.label}</div>
        <div style={{ fontSize:12, color:'#8b949e' }}>{node.id?.substring(0,8)}...</div>
      </div>

      {/* CRE-39: Pull-progress strip. Renders only while a pull is in flight. */}
      {pullActive && layerEntries.length > 0 && (
        <div style={{ background:'#0d1117', border:'1px solid #1f6feb', borderRadius:8, padding:'10px 12px', display:'flex', flexDirection:'column', gap:8 }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
            <span style={{ fontSize:11, color:'#58a6ff', textTransform:'uppercase', letterSpacing:1, fontWeight:600 }}>Pulling image</span>
            <span style={{ fontSize:11, color:'#58a6ff' }}>{overallPct}%</span>
          </div>
          {/* Overall bar */}
          <div style={{ background:'#21262d', height:6, borderRadius:3, overflow:'hidden' }}>
            <div style={{ background:'#1f6feb', height:'100%', width:`${overallPct}%`, transition:'width 200ms ease-out' }} />
          </div>
          {/* Per-layer detail (max 6 shown to keep panel tidy) */}
          <div style={{ display:'flex', flexDirection:'column', gap:4, maxHeight:120, overflowY:'auto' }}>
            {layerEntries.slice(0, 6).map(([lid, l]) => {
              const pct = l.total > 0 ? Math.round((l.current / l.total) * 100) : (l.complete ? 100 : 0)
              return (
                <div key={lid} style={{ display:'flex', flexDirection:'column', gap:2 }}>
                  <div style={{ display:'flex', justifyContent:'space-between', fontSize:10, color:'#8b949e', fontFamily:'monospace' }}>
                    <span>{lid === '_global' ? '·' : lid.substring(0, 12)}</span>
                    <span>{l.status}</span>
                  </div>
                  <div style={{ background:'#21262d', height:3, borderRadius:2, overflow:'hidden' }}>
                    <div style={{ background: l.complete ? '#3fb950' : '#58a6ff', height:'100%', width:`${pct}%`, transition:'width 200ms ease-out' }} />
                  </div>
                </div>
              )
            })}
            {layerEntries.length > 6 && (
              <div style={{ fontSize:10, color:'#8b949e', textAlign:'center', marginTop:2 }}>
                +{layerEntries.length - 6} more layers
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display:'flex', gap:0, borderBottom:'1px solid #21262d' }}>
        {['info','config'].map(tab => (
          <button key={tab} onClick={()=>setActiveTab(tab)} style={{
            background:'none', border:'none', borderBottom: activeTab===tab ? '2px solid #1d4ed8' : '2px solid transparent',
            color: activeTab===tab ? '#e6edf3' : '#8b949e',
            padding:'8px 14px', cursor:'pointer', fontSize:12, fontWeight:600, textTransform:'uppercase', letterSpacing:1
          }}>{tab}</button>
        ))}
      </div>

      {activeTab === 'info' && (
        <>
          <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
            {[['Type', data.type], ['Image', data.image], ['Status', data.status]].map(([l,v]) => (
              <div key={l} style={{ display:'flex', justifyContent:'space-between', fontSize:13 }}>
                <span style={{ color:'#8b949e' }}>{l}</span>
                <span style={{ color:'#e6edf3' }}>{v || '—'}</span>
              </div>
            ))}
          </div>

          <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
            <label style={{ fontSize:11, color:'#8b949e', textTransform:'uppercase', letterSpacing:1 }}>Node Name</label>
            <input
              value={name}
              onChange={e=>setName(e.target.value)}
              style={{ background:'#0d1117', border:'1px solid #21262d', color:'#e6edf3', padding:'6px 10px', borderRadius:6, fontSize:13 }}
            />
          </div>

          <div style={{ borderTop:'1px solid #21262d', paddingTop:12, display:'flex', flexDirection:'column', gap:6 }}>
            <button onClick={onStart} style={{ background:'#1a3a1a', border:'1px solid #3fb950', color:'#3fb950', padding:'7px', borderRadius:6, cursor:'pointer', fontSize:13 }}>▶ Start Node</button>
            <button onClick={onStop} style={{ background:'#21262d', border:'1px solid #30363d', color:'#8b949e', padding:'7px', borderRadius:6, cursor:'pointer', fontSize:13 }}>⬛ Stop Node</button>
            <button onClick={onOpenConsole} style={{ background:'#21262d', border:'1px solid #30363d', color:'#8b949e', padding:'7px', borderRadius:6, cursor:'pointer', fontSize:13 }}>▶ Open Console</button>

            {/* CRE-39: Open Web UI button. Renders only when the backend
                confirms the node has a web_port configured AND the node is
                running. We don't try to gate on running-status here because
                the proxy itself returns 409 if the node's stopped — let the
                backend be the source of truth and surface the error cleanly. */}
            {webInfo?.has_web_ui && (
              <button
                onClick={handleOpenWebUI}
                title={`Opens ${webInfo.web_scheme || 'http'}://...:${webInfo.web_port} via the lab reverse proxy`}
                style={{
                  background:'#0d2818', border:'1px solid #1f6feb', color:'#58a6ff',
                  padding:'7px', borderRadius:6, cursor:'pointer', fontSize:13,
                  display:'flex', alignItems:'center', justifyContent:'center', gap:6
                }}
              >
                <span>🌐</span>
                <span>Open Web UI</span>
                <span style={{ fontSize:10, color:'#8b949e' }}>:{webInfo.web_port}</span>
              </button>
            )}

            <button onClick={onDelete} style={{ background:'#2d1b1b', border:'1px solid #f85149', color:'#f85149', padding:'7px', borderRadius:6, cursor:'pointer', fontSize:13, marginTop:4 }}>🗑 Delete Node</button>
          </div>
        </>
      )}

      {activeTab === 'config' && (
        <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
          <label style={{ fontSize:11, color:'#8b949e', textTransform:'uppercase', letterSpacing:1 }}>Startup Configuration</label>
          <div style={{ fontSize:11, color:'#8b949e' }}>
            Commands or config applied when this node starts. Format depends on node type.
          </div>
          <textarea
            value={config}
            onChange={e=>setConfig(e.target.value)}
            placeholder={'# Example for Docker:\n# environment variables, startup commands\n#\n# Example for Cisco:\n# interface GigabitEthernet0/0\n#  ip address 10.1.1.1 255.255.255.0\n#  no shutdown'}
            style={{
              background:'#0d1117', border:'1px solid #21262d', color:'#e6edf3',
              padding:'10px', borderRadius:6, fontSize:12, fontFamily:'monospace',
              minHeight:240, resize:'vertical', lineHeight:1.5
            }}
          />
          <div style={{ display:'flex', gap:8, alignItems:'center' }}>
            <button onClick={handleSave} disabled={saving} style={{
              background: saved ? '#1a3a1a' : '#1d4ed8',
              border:'none', color:'#fff', padding:'8px 16px', borderRadius:6,
              cursor: saving ? 'wait' : 'pointer', fontSize:13, fontWeight:600,
              opacity: saving ? 0.6 : 1
            }}>
              {saving ? 'Saving...' : saved ? '✓ Saved' : 'Save Config'}
            </button>
            <span style={{ fontSize:11, color:'#8b949e' }}>{config.length} chars</span>
          </div>
        </div>
      )}
    </div>
  )
}
