import React, { useState, useEffect } from 'react'
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import Dashboard from './pages/Dashboard'
import LabCanvas from './pages/LabCanvas'
import Templates from './pages/Templates'
import SystemInfo from './pages/SystemInfo'
import HealthDashboard from './pages/HealthDashboard'
import Login from './pages/Login'
import ConsolePage from './pages/ConsolePage'
import VncPage from './pages/VncPage'
import RdpPage from './pages/RdpPage'
import FirstRunWizard from './pages/FirstRunWizard'
import StatusBadge from './components/StatusBadge'
import { getFirstRunStatus } from './utils/api'

export default function App() {
  const [authed, setAuthed] = useState(() => sessionStorage.getItem('omnilab_auth') === '1')
  // null = unknown (still loading), true/false once the GET resolves
  const [firstRunComplete, setFirstRunComplete] = useState(null)
  const navigate = useNavigate()
  const location = useLocation()

  // Probe /api/system/first-run once on mount. If the backend says we haven't
  // set up yet, force-redirect to /setup. This runs in parallel with the
  // existing auth gate — once setup is done the auth flow takes over.
  useEffect(() => {
    let cancelled = false
    getFirstRunStatus()
      .then((r) => {
        if (cancelled) return
        const complete = !!r?.data?.complete
        setFirstRunComplete(complete)
        if (!complete && location.pathname !== '/setup') {
          navigate('/setup', { replace: true })
        }
      })
      .catch(() => {
        // Backend unreachable or schema mismatch: don't block the app. Treat
        // as complete so the user can at least see Login/error state, but
        // log for visibility.
        if (cancelled) return
        // eslint-disable-next-line no-console
        console.warn('first-run probe failed; assuming setup complete')
        setFirstRunComplete(true)
      })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleLogout = () => {
    sessionStorage.removeItem('omnilab_auth')
    setAuthed(false)
  }

  // Setup route always wins over auth, console routes, etc.
  if (location.pathname === '/setup') {
    return (
      <Routes>
        <Route path="/setup" element={
          <FirstRunWizard onComplete={() => setFirstRunComplete(true)} />
        }/>
      </Routes>
    )
  }

  // Hold the screen until the first-run probe resolves. Short flash is
  // better than rendering Login and then yanking it away.
  if (firstRunComplete === null) {
    return (
      <div style={{
        minHeight: '100vh', background: '#0b0d12', color: '#9aa3b6',
        display: 'grid', placeItems: 'center', fontFamily: 'system-ui, sans-serif',
        fontSize: 14,
      }}>Loading OmniLab…</div>
    )
  }

  if (location.pathname.includes('/console/') || location.pathname.includes('/vnc/') || location.pathname.includes('/rdp/')) {
    return (
      <Routes>
        <Route path="/lab/:labId/console/:nodeId" element={<ConsolePage />} />
        <Route path="/lab/:labId/vnc/:nodeId" element={<VncPage />} />
        <Route path="/lab/:labId/rdp/:nodeId" element={<RdpPage />} />
      </Routes>
    )
  }
  if (!authed) {
    return (
      <Routes>
        <Route path="*" element={<Login onLogin={() => { sessionStorage.setItem('omnilab_auth','1'); setAuthed(true) }}/>}/>
      </Routes>
    )
  }

  return (
    <div style={{ display:'flex', height:'100vh', overflow:'hidden', background:'#0d1117' }}>
      <Sidebar onLogout={handleLogout}/>
      <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
        <TopBar/>
        <main style={{ flex:1, overflow:'auto' }}>
          <Routes>
            <Route path="/" element={<Dashboard/>}/>
            <Route path="/lab/:labId" element={<LabCanvas/>}/>
            <Route path="/templates" element={<Templates/>}/>
            <Route path="/system" element={<SystemInfo/>}/>
            <Route path="/health" element={<HealthDashboard/>}/>
          </Routes>
        </main>
      </div>
      <StatusBadge />
    </div>
  )
}
