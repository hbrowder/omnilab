import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

export default function RdpPage() {
  const { labId, nodeId } = useParams()
  const navigate = useNavigate()
  const [step, setStep] = useState('config')  // config | connecting | connected | error
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ host: '', port: '3389', username: '', password: '', domain: '' })

  const connect = async () => {
    if (!form.host) { setError('RDP host is required'); return }
    setStep('connecting')
    setError(null)
    try {
      const r = await fetch('/api/nodes/' + nodeId + '/rdp-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ host: form.host, port: parseInt(form.port) || 3389 }),
      })
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Config failed') }
      setStep('connected')
    } catch(e) { setError(e.message); setStep('config') }
  }

  const getGuacUrl = () => {
    const params = new URLSearchParams({
      'data-connection-id': nodeId,
      host: form.host,
      port: form.port,
      username: form.username,
      password: form.password,
      domain: form.domain,
    })
    return '/guacamole/#/' + '?' + params.toString()
  }

  const btn = (c, full) => ({
    background: full ? c : 'transparent',
    border: '1px solid ' + c,
    color: full ? '#0d1117' : c,
    borderRadius: 6, padding: '8px 20px', cursor: 'pointer', fontSize: 13, fontWeight: 600,
  })

  const inputStyle = {
    width: '100%', padding: '8px 12px', borderRadius: 6,
    background: '#0d1117', border: '1px solid #30363d', color: '#c9d1d9',
    fontSize: 13, boxSizing: 'border-box',
  }

  const field = (label, key, type='text', placeholder='') => (
    <div style={{ marginBottom: 12 }}>
      <div style={{ color: '#8b949e', fontSize: 11, marginBottom: 4 }}>{label}</div>
      <input type={type} value={form[key]} placeholder={placeholder}
        onChange={e => setForm(f => ({...f, [key]: e.target.value}))}
        style={inputStyle} />
    </div>
  )

  const header = (
    <div style={{ display:'flex', alignItems:'center', gap:12, padding:'8px 16px', background:'#161b22', borderBottom:'1px solid #30363d', flexShrink:0 }}>
      <button style={btn('#8b949e')} onClick={() => navigate('/lab/'+labId)}>&larr; Lab</button>
      <span style={{ color:'#58a6ff', fontWeight:600, fontSize:13 }}>[RDP] Console</span>
      <span style={{ color:'#8b949e', fontSize:11, fontFamily:'monospace' }}>{nodeId}</span>
      <div style={{ flex:1 }}/>
      {step==='connected' && <button style={btn('#ff7b72')} onClick={() => setStep('config')}>Disconnect</button>}
    </div>
  )

  if (step === 'connected') return (
    <div style={{ display:'flex', flexDirection:'column', height:'100vh', background:'#0d1117' }}>
      {header}
      <iframe
        src={'/guacamole/'}
        style={{ flex:1, border:'none', background:'#000' }}
        allow="clipboard-read; clipboard-write"
        title="RDP Console" />
    </div>
  )

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100vh', background:'#0d1117' }}>
      {header}
      <div style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center' }}>
        <div style={{ width: 420, background:'#161b22', border:'1px solid #30363d', borderRadius:12, padding:28 }}>
          <div style={{ color:'#58a6ff', fontWeight:700, fontSize:16, marginBottom:20 }}>RDP Connection</div>
          {error && <div style={{ color:'#ff7b72', fontSize:12, marginBottom:12, padding:'8px 12px', background:'rgba(255,123,114,0.1)', borderRadius:6 }}>{error}</div>}
          {field('RDP Host / IP *', 'host', 'text', '192.168.1.100')}
          {field('Port', 'port', 'number', '3389')}
          {field('Username', 'username', 'text', 'Administrator')}
          {field('Password', 'password', 'password', '')}
          {field('Domain (optional)', 'domain', 'text', '')}
          <div style={{ marginTop:20, display:'flex', gap:10 }}>
            <button style={btn('#8b949e')} onClick={() => navigate('/lab/'+labId)}>Cancel</button>
            <button style={btn('#58a6ff', true)} onClick={connect} disabled={step==='connecting'}>
              {step==='connecting' ? 'Connecting...' : 'Connect via RDP'}
            </button>
          </div>
          <div style={{ marginTop:16, color:'#6e7681', fontSize:11 }}>
            Powered by Apache Guacamole &mdash; clientless RDP in your browser
          </div>
        </div>
      </div>
    </div>
  )
}
