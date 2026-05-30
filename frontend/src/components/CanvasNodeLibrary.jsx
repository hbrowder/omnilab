import React, { useMemo, useState } from 'react'
import { VENDOR_GROUPS, NodeIcon, VendorBadge } from './VendorIcons'

// CRE-71 P3 (7): Persistent EVE-NG-style node-library sidebar.
// Canvas-local component (NOT the global app Sidebar). Collapsible left panel
// that replaces the modal node picker for fast, repeated node placement.
// Supports search, collapsible category sections, click-to-place, and
// HTML5 drag-and-drop onto the canvas.
//
// Props:
//   darkMode      bool
//   netDefs       NET_DEFS map { key: {label, color} } for network objects
//   onPickNode    (vendorType) => void   — click-to-place (opens qty dialog)
//   onPickNet     (netKey) => void       — click-to-place a network object
//   open          bool   — controlled open/collapsed state
//   onToggle      ()=>void
export default function CanvasNodeLibrary({ darkMode, netDefs={}, onPickNode, onPickNet, open, onToggle }) {
  const [query, setQuery] = useState('')
  const [collapsed, setCollapsed] = useState({}) // {category: true} when hidden

  const tc  = darkMode ? '#e2e8f0' : '#1e293b'
  const sc  = darkMode ? '#64748b' : '#6b7280'
  const bc  = darkMode ? '#334155' : '#e5e7eb'
  const panelBg = darkMode ? '#0f172a' : '#f8fafc'
  const itemHover = darkMode ? '#1e293b' : '#eef2ff'
  const inputBg = darkMode ? '#1e293b' : '#ffffff'

  const q = query.trim().toLowerCase()
  const groups = useMemo(() => {
    const out = {}
    Object.keys(VENDOR_GROUPS).forEach(cat => {
      const items = VENDOR_GROUPS[cat].filter(([key, def]) =>
        !q ||
        (def.label || '').toLowerCase().includes(q) ||
        (def.vendor || '').toLowerCase().includes(q) ||
        key.toLowerCase().includes(q)
      )
      if (items.length) out[cat] = items
    })
    return out
  }, [q])

  if (!open) {
    return (
      <div style={{ width: 28, background: panelBg, borderRight: '1px solid ' + bc, display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 8, flexShrink: 0 }}>
        <button onClick={onToggle} title="Open node library"
          style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)', background: 'none', border: 'none', color: sc, cursor: 'pointer', fontSize: 11, padding: '8px 2px', letterSpacing: 1 }}>
          ☰ NODE LIBRARY
        </button>
      </div>
    )
  }

  const dragStart = (e, kind, key) => {
    e.dataTransfer.setData('application/x-canvas-item', JSON.stringify({ kind, key }))
    e.dataTransfer.effectAllowed = 'copy'
  }

  const netEntries = Object.entries(netDefs)

  return (
    <div style={{ width: 230, background: panelBg, borderRight: '1px solid ' + bc, display: 'flex', flexDirection: 'column', flexShrink: 0, overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', padding: '8px 10px', borderBottom: '1px solid ' + bc, gap: 6 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: tc, letterSpacing: 0.5, flex: 1 }}>NODE LIBRARY</span>
        <button onClick={onToggle} title="Collapse library"
          style={{ background: 'none', border: 'none', color: sc, cursor: 'pointer', fontSize: 14, lineHeight: 1 }}>‹</button>
      </div>
      <div style={{ padding: '8px 10px', borderBottom: '1px solid ' + bc }}>
        <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search devices…"
          style={{ width: '100%', boxSizing: 'border-box', padding: '6px 8px', fontSize: 12, border: '1px solid ' + bc, borderRadius: 6, background: inputBg, color: tc, outline: 'none' }} />
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
        {netEntries.length > 0 && !q && (
          <div>
            <div style={{ padding: '6px 12px 4px', fontSize: 10, fontWeight: 700, color: sc, textTransform: 'uppercase', letterSpacing: 0.5 }}>Networks</div>
            {netEntries.map(([key, def]) => (
              <div key={key} draggable
                onDragStart={e => dragStart(e, 'net', key)}
                onClick={() => onPickNet && onPickNet(key)}
                title={`Add ${def.label} — click or drag onto canvas`}
                style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', cursor: 'grab', fontSize: 12, color: tc }}
                onMouseEnter={e => e.currentTarget.style.background = itemHover}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                <span style={{ width: 14, height: 14, borderRadius: 3, background: def.color, flexShrink: 0 }} />
                {def.label}
              </div>
            ))}
          </div>
        )}

        {Object.keys(groups).length === 0 && (
          <div style={{ padding: '14px 12px', fontSize: 12, color: sc }}>No devices match “{query}”.</div>
        )}

        {Object.keys(groups).map(cat => {
          const isCollapsed = collapsed[cat] && !q
          return (
            <div key={cat}>
              <div onClick={() => setCollapsed(c => ({ ...c, [cat]: !c[cat] }))}
                style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px 4px', fontSize: 10, fontWeight: 700, color: sc, textTransform: 'uppercase', letterSpacing: 0.5, cursor: 'pointer', userSelect: 'none' }}>
                <span style={{ fontSize: 9, width: 8 }}>{isCollapsed ? '▸' : '▾'}</span>
                {cat}
                <span style={{ fontWeight: 400 }}>({groups[cat].length})</span>
              </div>
              {!isCollapsed && groups[cat].map(([key, def]) => (
                <div key={key} draggable
                  onDragStart={e => dragStart(e, 'node', key)}
                  onClick={() => onPickNode && onPickNode(key)}
                  title={`${def.label} — click or drag onto canvas`}
                  style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 12px', cursor: 'grab' }}
                  onMouseEnter={e => e.currentTarget.style.background = itemHover}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <NodeIcon type={key} color={def.color} size={28} />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontSize: 12, fontWeight: 500, color: tc, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{def.label}</div>
                    <div style={{ marginTop: 1 }}><VendorBadge vendor={def.vendor} /></div>
                  </div>
                </div>
              ))}
            </div>
          )
        })}
      </div>
      <div style={{ padding: '6px 10px', borderTop: '1px solid ' + bc, fontSize: 10, color: sc }}>
        Click or drag a device onto the canvas
      </div>
    </div>
  )
}
