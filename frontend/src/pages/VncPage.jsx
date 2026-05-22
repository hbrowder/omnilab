import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

export default function VncPage() {
  const { labId, nodeId } = useParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState('starting')
  const [error, setError] = useState(null)
  const [nodeInfo, setNodeInfo] = useState(null)
  const iframeRef = useRef(null)

  useEffect(() => {
    fetch('/api/nodes/' + nodeId + '/start', { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        if (data.vnc_port) { setNodeInfo(data); setStatus('connected') }
        else if (data.status === 'running') { setError('PTY node: use text console instead'); setStatus('error') }
        else { setError(data.detail || 'Failed to start node'); setStatus('error') }
      })
      .catch(e => { setError('Start failed: ' + e.message); setStatus('error') })
    return () => { fetch('/api/nodes/' + nodeId + '/stop', { method: 'POST' }).catch(() => {}) }
  }, [nodeId])

  const getNoVncUrl = () => {
    const host = window.location.hostname
    const wsPath = 'api/console/' + nodeId + '/vnc-ws'
    return '/novnc/vnc_lite.html?host=' + host + '&port=5000&path=' + encodeURIComponent(wsPath) + '&autoconnect=1&reconnect=1'
  }

  const btn = (c) => ({ background:'transparent', border:'1px solid #30363d', color:c, borderRadius:6, padding:'4px 12px', cursor:'pointer', fontSize:12 })

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100vh', background:'#0d1117' }}>
      <div style={{ display:'flex', alignItems:'center', gap:12, padding:'8px 16px', background:'#161b22', borderBottom:'1px solid #30363d', flexShrink:0 }}>
        <button style={btn('#8b949e')} onClick={() => navigate('/lab/'+labId)}>&larr; Lab</button>
        <span style={{ color:'#58a6ff', fontWeight:600, fontSize:13 }}>[VNC] Console</span>
        <span style={{ color:'#8b949e', fontSize:11, fontFamily:'monospace' }}>{nodeId}</span>
        {nodeInfo?.vnc_port && <span style={{ color:'#3fb950', fontSize:11 }}>VNC :{nodeInfo.vnc_port}</span>}
        <div style={{ flex:1 }}/>
        <span style={{ fontSize:11, fontWeight:600, color: status==='connected'?'#3fb950':status==='error'?'#ff7b72':'#d29922' }}>
          {status==='starting'?'● Starting...':status==='connected'?'● Connected':'● Error'}
        </span>
      </div>
      <div style={{ flex:1, overflow:'hidden', position:'relative' }}>
        {status==='starting' && (
          <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center', flexDirection:'column', gap:16, color:'#8b949e' }}>
            <div style={{ fontSize:16, color:'#c9d1d9' }}>Starting QEMU VM...</div>
            <div style={{ fontSize:12 }}>Allocating VNC display and port</div>
          </div>
        )}
        {status==='error' && (
          <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center', flexDirection:'column', gap:16, color:'#ff7b72' }}>
            <div style={{ fontSize:16 }}>Failed to start VNC console</div>
            <div style={{ fontSize:12, color:'#8b949e', maxWidth:400, textAlign:'center' }}>{error}</div>
            <button style={btn('#58a6ff')} onClick={() => navigate('/lab/'+labId)}>&larr; Back to Lab</button>
          </div>
        )}
        {status==='connected' && (
          <iframe ref={iframeRef} src={getNoVncUrl()}
            style={{ width:'100%', height:'100%', border:'none', background:'#000' }}
            allow="clipboard-read; clipboard-write" title="VNC Console" />
        )}
      </div>
    </div>
  )
}
