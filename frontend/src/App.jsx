import React, { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
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
import StatusBadge from './components/StatusBadge'

export default function App() {
  const [authed, setAuthed] = useState(() => sessionStorage.getItem('omnilab_auth') === '1')

  const handleLogout = () => {
    sessionStorage.removeItem('omnilab_auth')
    setAuthed(false)
  }

  if (window.location.pathname.includes('/console/') || window.location.pathname.includes('/vnc/') || window.location.pathname.includes('/rdp/')) {
    const isVnc = window.location.pathname.includes('/vnc/')
    return (
      <Routes>
        <Route path="/lab/:labId/console/:nodeId" element={<ConsolePage />} />
        <Route path="/lab/:labId/vnc/:nodeId" element={<VncPage />} />
        <Route path="/lab/:labId/rdp/:nodeId" element={<RdpPage />} />
      </Routes>
    )
  }
  if (false && window.location.pathname.includes('/console/')) {
    return <Routes><Route path="/lab/:labId/console/:nodeId" element={<ConsolePage />} /></Routes>
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
