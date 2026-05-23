import React, { useState, useEffect, useRef } from 'react'


function OmniLogoFull() {
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:20 }}>
      <svg width="100" height="100" viewBox="0 0 100 100" style={{ filter: 'drop-shadow(0 0 20px rgba(29, 78, 216, 0.6))' }}>
        <defs>
          <linearGradient id="ring1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#1d4ed8', stopOpacity: 0.8 }} />
            <stop offset="50%" style={{ stopColor: '#3b82f6', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#1d4ed8', stopOpacity: 0.6 }} />
          </linearGradient>
          <linearGradient id="ring2" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#3b82f6', stopOpacity: 0.8 }} />
            <stop offset="50%" style={{ stopColor: '#60a5fa', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#3b82f6', stopOpacity: 0.6 }} />
          </linearGradient>
          <linearGradient id="ring3" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#93c5fd', stopOpacity: 0.7 }} />
            <stop offset="50%" style={{ stopColor: '#bfdbfe', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#93c5fd', stopOpacity: 0.5 }} />
          </linearGradient>
          <radialGradient id="sphere">
            <stop offset="0%" style={{ stopColor: '#60a5fa', stopOpacity: 1 }} />
            <stop offset="70%" style={{ stopColor: '#3b82f6', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#1d4ed8', stopOpacity: 1 }} />
          </radialGradient>
        </defs>
        <ellipse cx="50" cy="50" rx="44" ry="16" fill="none" stroke="url(#ring1)" strokeWidth="4" transform="rotate(-25 50 50)" opacity="0.9"/>
        <ellipse cx="50" cy="50" rx="44" ry="16" fill="none" stroke="url(#ring2)" strokeWidth="4" transform="rotate(35 50 50)" opacity="0.95"/>
        <ellipse cx="50" cy="50" rx="44" ry="16" fill="none" stroke="url(#ring3)" strokeWidth="4" transform="rotate(95 50 50)" opacity="0.85"/>
        <circle cx="50" cy="50" r="16" fill="url(#sphere)" filter="url(#glow)"/>
        <circle cx="50" cy="50" r="16" fill="url(#sphere)" opacity="0.4"/>
        <text x="50" y="55" fontFamily="Arial,sans-serif" fontSize="16" fontWeight="800" fill="white" textAnchor="middle" style={{ textShadow: '0 0 10px rgba(96, 165, 250, 0.8)' }}>O</text>
      </svg>
      <div style={{ textAlign:'center' }}>
        <div style={{ display:'flex', alignItems:'baseline', justifyContent:'center', gap:0 }}>
          <span style={{ fontWeight:800, fontSize:52, color:'#ffffff', letterSpacing:'-2px', fontFamily:'system-ui,sans-serif', lineHeight:1 }}>OMNI</span>
          <span style={{ fontWeight:800, fontSize:52, color:'#6b7280', letterSpacing:'12px', fontFamily:'system-ui,sans-serif', lineHeight:1 }}>LAB</span>
        </div>
        <div style={{ width:'100%', height:3, background:'#1d4ed8', borderRadius:2, marginTop:6 }}/>
        <div style={{ marginTop:10, fontSize:12, color:'#58a6ff', letterSpacing:'3px', fontFamily:'monospace', fontWeight:600 }}>
          OPEN MULTI-NODE INFRASTRUCTURE LAB
        </div>
        <div style={{ marginTop:8, fontSize:16, color:'#c9d1d9', fontStyle:'italic', letterSpacing:'0.5px' }}>
          Every node. Every stack. One lab.
        </div>
      </div>
    </div>
  )
}

export default function Login({ onLogin }) {
  
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPass, setShowPass] = useState(false)
  const [error, setError] = useState('')
  const topoCanvasRef = useRef(null)
  useEffect(() => {
    const canvas = topoCanvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let W = 0, H = 0
    const dpr = Math.max(1, window.devicePixelRatio || 1)
    let rafId = 0
    const resize = () => {
      const r = canvas.getBoundingClientRect()
      W = r.width; H = r.height
      canvas.width = W * dpr; canvas.height = H * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)
    const NODE_COUNT = 40
    const nodes = []
    for (let i = 0; i < NODE_COUNT; i++) {
      nodes.push({
        x: Math.random(), y: Math.random(),
        vx: (Math.random() - 0.5) * 0.00012,
        vy: (Math.random() - 0.5) * 0.00012,
        r: 1.4 + Math.random() * 1.6
      })
    }
    const LINK_DIST = 0.20
    const packets = []
    const spawnPacket = () => {
      const a = nodes[Math.floor(Math.random() * nodes.length)]
      const cand = nodes.filter(n => n !== a && Math.hypot(n.x - a.x, n.y - a.y) < LINK_DIST)
      if (!cand.length) return
      const b = cand[Math.floor(Math.random() * cand.length)]
      packets.push({ a, b, t: 0, speed: 0.004 + Math.random() * 0.006 })
    }
    for (let i = 0; i < 8; i++) spawnPacket()
    let last = performance.now()
    const frame = (now) => {
      const dt = Math.min(40, now - last); last = now
      ctx.clearRect(0, 0, W, H)
      for (const n of nodes) {
        n.x += n.vx * dt; n.y += n.vy * dt
        if (n.x < 0 || n.x > 1) n.vx *= -1
        if (n.y < 0 || n.y > 1) n.vy *= -1
      }
      ctx.lineWidth = 1
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j]
          const d = Math.hypot(a.x - b.x, a.y - b.y)
          if (d < LINK_DIST) {
            const alpha = (1 - d / LINK_DIST) * 0.35
            ctx.strokeStyle = 'rgba(59,130,246,' + alpha.toFixed(3) + ')'
            ctx.beginPath()
            ctx.moveTo(a.x * W, a.y * H)
            ctx.lineTo(b.x * W, b.y * H)
            ctx.stroke()
          }
        }
      }
      for (const n of nodes) {
        ctx.fillStyle = 'rgba(125,167,224,0.65)'
        ctx.beginPath()
        ctx.arc(n.x * W, n.y * H, n.r, 0, Math.PI * 2)
        ctx.fill()
      }
      for (let i = packets.length - 1; i >= 0; i--) {
        const p = packets[i]
        p.t += p.speed * (dt / 16)
        if (p.t >= 1) { packets.splice(i, 1); continue }
        const x = (p.a.x + (p.b.x - p.a.x) * p.t) * W
        const y = (p.a.y + (p.b.y - p.a.y) * p.t) * H
        ctx.fillStyle = 'rgba(96,165,250,1)'
        ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill()
        ctx.fillStyle = 'rgba(96,165,250,0.3)'
        ctx.beginPath(); ctx.arc(x, y, 5.5, 0, Math.PI * 2); ctx.fill()
      }
      if (Math.random() < 0.04) spawnPacket()
      rafId = requestAnimationFrame(frame)
    }
    rafId = requestAnimationFrame(frame)
    return () => {
      cancelAnimationFrame(rafId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setTimeout(() => {
      if (username === 'admin' && password === 'admin') {
        onLogin()
      } else {
        setError('Invalid credentials. Default: admin / admin')
        setLoading(false)
      }
    }, 800)
  }

  return (
    <div style={{
      minHeight:'100vh', background:'#050d1a',
      display:'flex', alignItems:'center', justifyContent:'center',
      fontFamily:'system-ui,sans-serif', position:'relative', overflow:'hidden'
    }}>

      <canvas ref={topoCanvasRef} style={{ position:'absolute', inset:0, width:'100%', height:'100%', display:'block' }} />
      <div style={{ position:'absolute', inset:0, background:'radial-gradient(ellipse at center, rgba(5,13,26,0) 0%, rgba(5,13,26,0.75) 100%)', pointerEvents:'none' }} />

      <div style={{ position:'relative', zIndex:10, width:'100%', maxWidth:420, padding:'0 24px' }}>

        <div style={{ marginBottom:40 }}>
          <OmniLogoFull/>
        </div>

        <div style={{ background:'rgba(13,17,23,0.9)', border:'1px solid #21262d', borderRadius:12, padding:32, backdropFilter:'blur(10px)' }}>
          <div style={{ fontSize:16, fontWeight:600, color:'#e6edf3', marginBottom:4, textAlign:'center' }}>Sign in to your session</div>
          <div style={{ fontSize:12, color:'#6b7280', marginBottom:24, textAlign:'center' }}>OmniLab v1.0.0</div>

          {error && (
            <div style={{ background:'#2d1515', border:'1px solid #f85149', borderRadius:6, padding:'8px 12px', fontSize:12, color:'#f85149', marginBottom:16 }}>
              {error}
            </div>
          )}

          <form onSubmit={handleLogin}>
            <div style={{ marginBottom:14 }}>
              <label style={{ fontSize:12, color:'#8b949e', display:'block', marginBottom:6 }}>Username</label>
              <div style={{ position:'relative' }}>
                <input
                  type="text" value={username} onChange={e => setUsername(e.target.value)}
                  placeholder="Enter username"
                  style={{ width:'100%', background:'#161b22', border:'1px solid #30363d', borderRadius:6, padding:'10px 14px 10px 38px', color:'#e6edf3', fontSize:14, outline:'none', boxSizing:'border-box' }}
                  onFocus={e => e.target.style.borderColor='#3b82f6'}
                  onBlur={e => e.target.style.borderColor='#30363d'}
                />
                <span style={{ position:'absolute', left:12, top:'50%', transform:'translateY(-50%)', fontSize:16, color:'#8b949e' }}>👤</span>
              </div>
            </div>

            <div style={{ marginBottom:24 }}>
              <label style={{ fontSize:12, color:'#8b949e', display:'block', marginBottom:6 }}>Password</label>
              <div style={{ position:'relative' }}>
                <input
                  type={showPass ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="Enter password"
                  style={{ width:'100%', background:'#161b22', border:'1px solid #30363d', borderRadius:6, padding:'10px 40px 10px 38px', color:'#e6edf3', fontSize:14, outline:'none', boxSizing:'border-box' }}
                  onFocus={e => e.target.style.borderColor='#3b82f6'}
                  onBlur={e => e.target.style.borderColor='#30363d'}
                />
                <span style={{ position:'absolute', left:12, top:'50%', transform:'translateY(-50%)', fontSize:16, color:'#8b949e' }}>🔒</span>
                <span onClick={() => setShowPass(s => !s)} style={{ position:'absolute', right:12, top:'50%', transform:'translateY(-50%)', fontSize:14, color:'#8b949e', cursor:'pointer' }}>{showPass ? '🙈' : '👁'}</span>
              </div>
            </div>

            <button type="submit" disabled={loading}
              style={{ width:'100%', padding:'12px', background: loading ? '#1d4ed844' : '#1d4ed8', color:'white', border:'none', borderRadius:6, fontSize:15, fontWeight:600, cursor: loading ? 'default' : 'pointer', letterSpacing:'0.5px' }}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div style={{ marginTop:20, display:'flex', justifyContent:'center', gap:16, flexWrap:'wrap' }}>
            {['Security','DevOps','Networking','Cloud','AI/ML','Training'].map(tag => (
              <span key={tag} style={{ fontSize:10, color:'#8b949e', letterSpacing:'1px', fontWeight:500 }}>{tag}</span>
            ))}
          </div>
        </div>

        <div style={{ textAlign:'center', marginTop:20, fontSize:11, color:'#8b949e' }}>
          © 2026 OmniLab — Open Multi-Node Infrastructure Lab
        </div>
      </div>
    </div>
  )
}
