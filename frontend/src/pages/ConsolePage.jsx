
import { useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Terminal } from 'xterm'
import { FitAddon } from '@xterm/addon-fit'
import 'xterm/css/xterm.css'

export default function ConsolePage() {
  const { labId, nodeId } = useParams()
  const navigate = useNavigate()
  const termRef  = useRef(null)
  const xtermRef = useRef(null)
  const fitRef   = useRef(null)
  const wsRef    = useRef(null)
  const liveRef  = useRef(false)

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState < 2) return
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(proto+'//'+window.location.hostname+':5000/api/console/'+nodeId+'/ws')
    ws.binaryType = 'arraybuffer'
    wsRef.current = ws
    const term = xtermRef.current
    ws.onopen = () => {
      liveRef.current = true
      term.write('\r\n\x1b[32m● Connected\x1b[0m\r\n\r\n')
      if (fitRef.current) {
        fitRef.current.fit()
        ws.send(JSON.stringify({ type: 'resize', rows: term.rows, cols: term.cols }))
      }
    }
    ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) term.write(new Uint8Array(ev.data))
      else term.write(ev.data)
    }
    ws.onclose = () => {
      liveRef.current = false
      term.write('\r\n\x1b[33m● Disconnected — press any key to reconnect\x1b[0m\r\n')
    }
    ws.onerror = () => term.write('\r\n\x1b[31m● Connection error\x1b[0m\r\n')
  }, [nodeId])

  useEffect(() => {
    const term = new Terminal({
      theme: {
        background: '#0d1117', foreground: '#c9d1d9', cursor: '#58a6ff',
        black: '#484f58', red: '#ff7b72', green: '#3fb950', yellow: '#d29922',
        blue: '#58a6ff', magenta: '#bc8cff', cyan: '#39c5cf', white: '#b1bac4',
        brightBlack: '#6e7681', brightRed: '#ffa198', brightGreen: '#56d364',
        brightYellow: '#e3b341', brightBlue: '#79c0ff', brightMagenta: '#d2a8ff',
        brightCyan: '#56d4dd', brightWhite: '#f0f6fc',
      },
      fontFamily: "'JetBrains Mono','Fira Code','Cascadia Code',monospace",
      fontSize: 14, lineHeight: 1.2, cursorBlink: true, cursorStyle: 'block',
      scrollback: 5000, allowTransparency: true,
    })
    const fit = new FitAddon()
    term.loadAddon(fit)
    xtermRef.current = term
    fitRef.current   = fit
    term.open(termRef.current)
    fit.fit()
    term.write('\x1b[1;34m OmniLab Node Console\x1b[0m\r\n')
    term.write('\x1b[2m Node: '+nodeId+'\x1b[0m\r\n\r\n')
    term.onData((d) => {
      if (wsRef.current && wsRef.current.readyState === 1)
        wsRef.current.send(new TextEncoder().encode(d))
      else if (!liveRef.current) connect()
    })
    const onResize = () => {
      fit.fit()
      if (wsRef.current && wsRef.current.readyState === 1)
        wsRef.current.send(JSON.stringify({ type: 'resize', rows: term.rows, cols: term.cols }))
    }
    window.addEventListener('resize', onResize)
    connect()
    return () => {
      window.removeEventListener('resize', onResize)
      if (wsRef.current) wsRef.current.close()
      term.dispose()
    }
  }, [connect, nodeId])

  const btn = (c) => ({ background:'transparent', border:'1px solid #30363d', color:c, borderRadius:6, padding:'4px 12px', cursor:'pointer', fontSize:12 })

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100vh', background:'#0d1117' }}>
      <div style={{ display:'flex', alignItems:'center', gap:12, padding:'8px 16px', background:'#161b22', borderBottom:'1px solid #30363d', flexShrink:0 }}>
        <button style={btn('#8b949e')} onClick={() => navigate('/lab/'+labId)}>← Lab</button>
        <span style={{ color:'#58a6ff', fontWeight:600, fontSize:13 }}>⬛ Console</span>
        <span style={{ color:'#8b949e', fontSize:11, fontFamily:'monospace' }}>{nodeId}</span>
        <div style={{ flex:1 }}/>
        <button style={btn('#3fb950')} onClick={connect}>↻ Reconnect</button>
      </div>
      <div style={{ flex:1, overflow:'hidden', padding:8 }}>
        <div ref={termRef} style={{ width:'100%', height:'100%' }} />
      </div>
    </div>
  )
}
