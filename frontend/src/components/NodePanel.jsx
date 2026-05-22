import React, { useState, useEffect } from 'react'
import { updateNodeConfig } from '../utils/api'

export default function NodePanel({ node, onDelete, onClose, onStart, onStop, onOpenConsole, onSaved }) {
  const data = node.data || {}
  const [config, setConfig] = useState('')
  const [name, setName] = useState(data.label || '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [activeTab, setActiveTab] = useState('info')

  useEffect(() => {
    // Load existing config
    setConfig(data.config || '')
    setName(data.label || '')
    setSaved(false)
  }, [node.id])

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
