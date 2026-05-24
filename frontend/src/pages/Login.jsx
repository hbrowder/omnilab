import React, { useState, useEffect, useRef } from 'react'


function OmniLogoFull() {
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:20 }}>
      <svg width="480" height="480" viewBox="0 0 400 400" style={{ filter: 'drop-shadow(0 0 40px rgba(0, 217, 255, 0.6))' }}>
        <defs>
          <radialGradient id="darkCore">
            <stop offset="0%" style={{ stopColor: '#1e3a5f', stopOpacity: 1 }} />
            <stop offset="40%" style={{ stopColor: '#0f2847', stopOpacity: 1 }} />
            <stop offset="70%" style={{ stopColor: '#0a1628', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#050b14', stopOpacity: 1 }} />
          </radialGradient>
          
          {/* Sphere lighting gradient - creates 3D effect */}
          <radialGradient id="sphereLighting" cx="35%" cy="35%">
            <stop offset="0%" style={{ stopColor: '#ffffff', stopOpacity: 0.4 }} />
            <stop offset="30%" style={{ stopColor: '#93c5fd', stopOpacity: 0.2 }} />
            <stop offset="60%" style={{ stopColor: '#1e40af', stopOpacity: 0.1 }} />
            <stop offset="100%" style={{ stopColor: '#000000', stopOpacity: 0.5 }} />
          </radialGradient>
          
          {/* Global network visualization pattern */}
          <pattern id="sphereTexture" x="0" y="0" width="100" height="100" patternUnits="userSpaceOnUse">
            {/* ETHERNET CABLES - Thick cables with ribbed texture spanning the globe */}
            
            {/* Cable 1 - with ribbed segments */}
            <line x1="10" y1="20" x2="50" y2="45" stroke="#e0e0e0" strokeWidth="2.5" opacity="0.3" strokeLinecap="round"/>
            <line x1="10" y1="20" x2="50" y2="45" stroke="#ffffff" strokeWidth="2" opacity="0.9" strokeDasharray="3 1.5" strokeLinecap="round">
              <animate attributeName="stroke" values="#ffffff;#bfdbfe;#ffffff" dur="2.5s" repeatCount="indefinite"/>
            </line>
            
            {/* Cable 2 */}
            <line x1="50" y1="45" x2="85" y2="35" stroke="#e0e0e0" strokeWidth="2.5" opacity="0.3" strokeLinecap="round"/>
            <line x1="50" y1="45" x2="85" y2="35" stroke="#ffffff" strokeWidth="2" opacity="0.9" strokeDasharray="3 1.5" strokeLinecap="round">
              <animate attributeName="stroke" values="#ffffff;#93c5fd;#ffffff" dur="3s" repeatCount="indefinite"/>
            </line>
            
            {/* Cable 3 */}
            <line x1="20" y1="65" x2="60" y2="75" stroke="#e0e0e0" strokeWidth="2.2" opacity="0.3" strokeLinecap="round"/>
            <line x1="20" y1="65" x2="60" y2="75" stroke="#ffffff" strokeWidth="1.8" opacity="0.85" strokeDasharray="3 1.5" strokeLinecap="round">
              <animate attributeName="stroke" values="#ffffff;#bfdbfe;#ffffff" dur="2.8s" repeatCount="indefinite"/>
            </line>
            
            {/* Cable 4 */}
            <line x1="60" y1="15" x2="75" y2="50" stroke="#e0e0e0" strokeWidth="2.3" opacity="0.3" strokeLinecap="round"/>
            <line x1="60" y1="15" x2="75" y2="50" stroke="#ffffff" strokeWidth="1.9" opacity="0.8" strokeDasharray="3 1.5" strokeLinecap="round">
              <animate attributeName="stroke" values="#ffffff;#93c5fd;#ffffff" dur="3.2s" repeatCount="indefinite"/>
            </line>
            
            {/* Cable 5 */}
            <line x1="15" y1="35" x2="45" y2="45" stroke="#e0e0e0" strokeWidth="2.4" opacity="0.3" strokeLinecap="round"/>
            <line x1="15" y1="35" x2="45" y2="45" stroke="#ffffff" strokeWidth="2" opacity="0.9" strokeDasharray="3 1.5" strokeLinecap="round">
              <animate attributeName="stroke" values="#ffffff;#bfdbfe;#ffffff" dur="2.3s" repeatCount="indefinite"/>
            </line>
            
            {/* Cable 6 */}
            <line x1="45" y1="45" x2="70" y2="70" stroke="#e0e0e0" strokeWidth="2.3" opacity="0.3" strokeLinecap="round"/>
            <line x1="45" y1="45" x2="70" y2="70" stroke="#ffffff" strokeWidth="1.9" opacity="0.85" strokeDasharray="3 1.5" strokeLinecap="round">
              <animate attributeName="stroke" values="#ffffff;#93c5fd;#ffffff" dur="2.7s" repeatCount="indefinite"/>
            </line>
            
            {/* Cable 7 */}
            <line x1="30" y1="25" x2="82" y2="48" stroke="#e0e0e0" strokeWidth="2.2" opacity="0.3" strokeLinecap="round"/>
            <line x1="30" y1="25" x2="82" y2="48" stroke="#ffffff" strokeWidth="1.8" opacity="0.8" strokeDasharray="3 1.5" strokeLinecap="round">
              <animate attributeName="stroke" values="#ffffff;#bfdbfe;#ffffff" dur="3.5s" repeatCount="indefinite"/>
            </line>
            
            {/* Cable 8 */}
            <line x1="12" y1="75" x2="55" y2="20" stroke="#e0e0e0" strokeWidth="2.4" opacity="0.3" strokeLinecap="round"/>
            <line x1="12" y1="75" x2="55" y2="20" stroke="#ffffff" strokeWidth="2" opacity="0.9" strokeDasharray="3 1.5" strokeLinecap="round">
              <animate attributeName="stroke" values="#ffffff;#93c5fd;#ffffff" dur="2.6s" repeatCount="indefinite"/>
            </line>
            
            {/* Network nodes - connection points - BRIGHTER */}
            <circle cx="10" cy="20" r="2" fill="#00d9ff" opacity="1">
              <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite"/>
              <animate attributeName="r" values="2;2.5;2" dur="2s" repeatCount="indefinite"/>
            </circle>
            <circle cx="50" cy="45" r="2.5" fill="#ffffff" opacity="1">
              <animate attributeName="opacity" values="1;0.5;1" dur="2.5s" repeatCount="indefinite"/>
              <animate attributeName="r" values="2.5;3;2.5" dur="2.5s" repeatCount="indefinite"/>
            </circle>
            <circle cx="85" cy="35" r="2" fill="#00d9ff" opacity="1">
              <animate attributeName="opacity" values="1;0.4;1" dur="3s" repeatCount="indefinite"/>
              <animate attributeName="r" values="2;2.5;2" dur="3s" repeatCount="indefinite"/>
            </circle>
            <circle cx="20" cy="65" r="1.8" fill="#3b82f6" opacity="1">
              <animate attributeName="opacity" values="1;0.5;1" dur="2.2s" repeatCount="indefinite"/>
              <animate attributeName="r" values="1.8;2.3;1.8" dur="2.2s" repeatCount="indefinite"/>
            </circle>
            <circle cx="60" cy="75" r="2" fill="#60a5fa" opacity="1">
              <animate attributeName="opacity" values="1;0.4;1" dur="2.8s" repeatCount="indefinite"/>
              <animate attributeName="r" values="2;2.5;2" dur="2.8s" repeatCount="indefinite"/>
            </circle>
            <circle cx="60" cy="15" r="1.8" fill="#3b82f6" opacity="1">
              <animate attributeName="opacity" values="1;0.5;1" dur="3.2s" repeatCount="indefinite"/>
              <animate attributeName="r" values="1.8;2.3;1.8" dur="3.2s" repeatCount="indefinite"/>
            </circle>
            <circle cx="75" cy="50" r="2" fill="#00d9ff" opacity="1">
              <animate attributeName="opacity" values="1;0.4;1" dur="2.6s" repeatCount="indefinite"/>
              <animate attributeName="r" values="2;2.5;2" dur="2.6s" repeatCount="indefinite"/>
            </circle>
            <circle cx="70" cy="70" r="1.8" fill="#60a5fa" opacity="1">
              <animate attributeName="opacity" values="1;0.5;1" dur="2.4s" repeatCount="indefinite"/>
              <animate attributeName="r" values="1.8;2.3;1.8" dur="2.4s" repeatCount="indefinite"/>
            </circle>
            <circle cx="30" cy="25" r="1.9" fill="#3b82f6" opacity="1">
              <animate attributeName="opacity" values="1;0.4;1" dur="2.7s" repeatCount="indefinite"/>
              <animate attributeName="r" values="1.9;2.4;1.9" dur="2.7s" repeatCount="indefinite"/>
            </circle>
            <circle cx="82" cy="48" r="2" fill="#00d9ff" opacity="1">
              <animate attributeName="opacity" values="1;0.5;1" dur="3.1s" repeatCount="indefinite"/>
              <animate attributeName="r" values="2;2.5;2" dur="3.1s" repeatCount="indefinite"/>
            </circle>
          </pattern>
          <linearGradient id="labGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style={{ stopColor: '#ffffff', stopOpacity: 1 }}>
              <animate attributeName="stop-color" values="#ffffff; #00d9ff; #0080ff; #00d9ff; #ffffff" dur="4s" repeatCount="indefinite"/>
            </stop>
            <stop offset="50%" style={{ stopColor: '#00d9ff', stopOpacity: 1 }}>
              <animate attributeName="stop-color" values="#00d9ff; #0080ff; #0040a0; #0080ff; #00d9ff" dur="4s" repeatCount="indefinite"/>
            </stop>
            <stop offset="100%" style={{ stopColor: '#0080ff', stopOpacity: 1 }}>
              <animate attributeName="stop-color" values="#0080ff; #0040a0; #003080; #0040a0; #0080ff" dur="4s" repeatCount="indefinite"/>
            </stop>
          </linearGradient>
          <linearGradient id="omniGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style={{ stopColor: '#ffffff', stopOpacity: 1 }}>
              <animate attributeName="stop-color" values="#ffffff; #e0f2fe; #bfdbfe; #e0f2fe; #ffffff" dur="3.5s" repeatCount="indefinite"/>
            </stop>
            <stop offset="50%" style={{ stopColor: '#f0f9ff', stopOpacity: 1 }}>
              <animate attributeName="stop-color" values="#f0f9ff; #bfdbfe; #93c5fd; #bfdbfe; #f0f9ff" dur="3.5s" repeatCount="indefinite"/>
            </stop>
            <stop offset="100%" style={{ stopColor: '#e0f2fe', stopOpacity: 1 }}>
              <animate attributeName="stop-color" values="#e0f2fe; #93c5fd; #60a5fa; #93c5fd; #e0f2fe" dur="3.5s" repeatCount="indefinite"/>
            </stop>
          </linearGradient>
          <linearGradient id="energyRing1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#00d9ff', stopOpacity: 0.2 }} />
            <stop offset="30%" style={{ stopColor: '#00d9ff', stopOpacity: 0.9 }} />
            <stop offset="50%" style={{ stopColor: '#ffffff', stopOpacity: 1 }}>
              <animate attributeName="offset" values="0.5;0.7;0.9;0.1;0.3;0.5" dur="4s" repeatCount="indefinite"/>
            </stop>
            <stop offset="70%" style={{ stopColor: '#00d9ff', stopOpacity: 0.9 }} />
            <stop offset="100%" style={{ stopColor: '#00d9ff', stopOpacity: 0.2 }} />
          </linearGradient>
          <linearGradient id="energyRing2" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#0080ff', stopOpacity: 0.2 }} />
            <stop offset="30%" style={{ stopColor: '#0080ff', stopOpacity: 0.9 }} />
            <stop offset="50%" style={{ stopColor: '#60a5fa', stopOpacity: 1 }}>
              <animate attributeName="offset" values="0.5;0.75;0.95;0.15;0.35;0.5" dur="5s" repeatCount="indefinite"/>
            </stop>
            <stop offset="70%" style={{ stopColor: '#0080ff', stopOpacity: 0.9 }} />
            <stop offset="100%" style={{ stopColor: '#0080ff', stopOpacity: 0.2 }} />
          </linearGradient>
          <linearGradient id="energyRing3" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#0040a0', stopOpacity: 0.3 }} />
            <stop offset="30%" style={{ stopColor: '#3b82f6', stopOpacity: 0.85 }} />
            <stop offset="50%" style={{ stopColor: '#93c5fd', stopOpacity: 0.95 }}>
              <animate attributeName="offset" values="0.5;0.8;0.1;0.4;0.5" dur="6s" repeatCount="indefinite"/>
            </stop>
            <stop offset="70%" style={{ stopColor: '#3b82f6', stopOpacity: 0.85 }} />
            <stop offset="100%" style={{ stopColor: '#0040a0', stopOpacity: 0.3 }} />
          </linearGradient>
          <filter id="energyGlow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          <filter id="strongGlow">
            <feGaussianBlur stdDeviation="8" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        <style>
          {`
            @keyframes pulse1 { 0%, 100% { opacity: 0.3; } 50% { opacity: 0.9; } }
            @keyframes pulse2 { 0%, 100% { opacity: 0.4; } 50% { opacity: 0.8; } }
            @keyframes pulse3 { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
            .particle1 { animation: pulse1 3s ease-in-out infinite; }
            .particle2 { animation: pulse2 2.5s ease-in-out infinite 0.5s; }
            .particle3 { animation: pulse3 3.5s ease-in-out infinite 1s; }
          `}
        </style>
        
        {/* Outer particle field - pulsating */}
        <circle cx="80" cy="100" r="2" fill="#00d9ff" className="particle1"/>
        <circle cx="320" cy="120" r="1.5" fill="#60a5fa" className="particle2"/>
        <circle cx="120" cy="330" r="2.5" fill="#00d9ff" className="particle3"/>
        <circle cx="280" cy="340" r="2" fill="#3b82f6" className="particle1"/>
        <circle cx="350" cy="200" r="1.8" fill="#00d9ff" className="particle2"/>
        <circle cx="60" cy="260" r="2" fill="#60a5fa" className="particle3"/>
        <circle cx="370" cy="280" r="1.5" fill="#3b82f6" className="particle1"/>
        <circle cx="50" cy="150" r="2.2" fill="#00d9ff" className="particle2"/>
        
        {/* Background rings - electric energy flowing */}
        <ellipse cx="200" cy="200" rx="150" ry="55" fill="none" stroke="url(#energyRing3)" strokeWidth="8" transform="rotate(95 200 200)" opacity="0.7" filter="url(#energyGlow)"/>
        
        {/* Mid-layer ring - electric energy */}
        <ellipse cx="200" cy="200" rx="150" ry="55" fill="none" stroke="url(#energyRing2)" strokeWidth="10" transform="rotate(35 200 200)" opacity="0.9" filter="url(#strongGlow)"/>
        
        {/* Foreground ring - electric energy */}
        <ellipse cx="200" cy="200" rx="150" ry="55" fill="none" stroke="url(#energyRing1)" strokeWidth="12" transform="rotate(-25 200 200)" opacity="1" filter="url(#strongGlow)"/>
        
        {/* Intersection glow points */}
        <circle cx="200" cy="95" r="6" fill="#00d9ff" opacity="0.8" filter="url(#strongGlow)" className="particle3"/>
        <circle cx="200" cy="305" r="6" fill="#00d9ff" opacity="0.8" filter="url(#strongGlow)" className="particle2"/>
        <circle cx="95" cy="200" r="5" fill="#60a5fa" opacity="0.7" filter="url(#energyGlow)" className="particle1"/>
        <circle cx="305" cy="200" r="5" fill="#60a5fa" opacity="0.7" filter="url(#energyGlow)" className="particle3"/>
        
        {/* Energy particles near core - pulsating */}
        <circle cx="160" cy="170" r="3" fill="#00d9ff" className="particle2"/>
        <circle cx="240" cy="220" r="2.5" fill="#60a5fa" className="particle1"/>
        <circle cx="175" cy="235" r="2.8" fill="#00d9ff" className="particle3"/>
        <circle cx="225" cy="165" r="3.2" fill="#3b82f6" className="particle2"/>
        
        {/* Dark center core - 3D sphere effect */}
        <circle cx="200" cy="200" r="70" fill="url(#darkCore)" opacity="0.95"/>
        
        {/* Rotating texture layer */}
        <circle cx="200" cy="200" r="70" fill="url(#sphereTexture)" opacity="0.6">
          <animateTransform attributeName="transform" type="rotate" from="0 200 200" to="360 200 200" dur="30s" repeatCount="indefinite"/>
        </circle>
        
        {/* 3D lighting overlay */}
        <circle cx="200" cy="200" r="70" fill="url(#sphereLighting)" opacity="0.85"/>
        
        {/* Text content - properly centered */}
        <text x="200" y="180" fontFamily="system-ui,sans-serif" fontSize="38" fontWeight="800" textAnchor="middle">
          <tspan fill="url(#omniGradient)" letterSpacing="-1px">OMNI</tspan><tspan fill="url(#labGradient)" letterSpacing="2px">LAB</tspan>
        </text>
        
        <text x="200" y="203" fontFamily="monospace" fontSize="11" fontWeight="700" fill="#00d9ff" textAnchor="middle" letterSpacing="0.8px">OPEN MULTI-NODE</text>
        <text x="200" y="217" fontFamily="monospace" fontSize="11" fontWeight="700" fill="#00d9ff" textAnchor="middle" letterSpacing="0.8px">INFRASTRUCTURE LAB</text>
        
        <text x="200" y="238" fontFamily="system-ui,sans-serif" fontSize="13" fontWeight="400" fill="#c9d1d9" textAnchor="middle" fontStyle="italic" letterSpacing="0.3px">Every node. Every stack. One lab.</text>
      </svg>
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

        <div style={{ marginBottom:8 }}>
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
