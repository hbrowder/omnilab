import React, { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import { createLab, getLabs } from '../utils/api'
import { PromptModal } from './Modal'

const TITLES = { '/':'Dashboard', '/templates':'Lab Templates', '/system':'System Info' }

export default function TopBar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { activeLab, setLabs } = useStore()
  const [showNamePrompt, setShowNamePrompt] = useState(false)
  const [showCategoryPrompt, setShowCategoryPrompt] = useState(false)
  const [labName, setLabName] = useState('')
  
  const title = activeLab && location.pathname.startsWith('/lab/') ? activeLab.name : TITLES[location.pathname] || 'OmniLab'
  
  const handleNewLab = () => {
    setShowNamePrompt(true)
  }
  
  const handleNameSubmit = (name) => {
    setLabName(name)
    setShowNamePrompt(false)
    setShowCategoryPrompt(true)
  }
  
  const handleCategorySubmit = async (category) => {
    setShowCategoryPrompt(false)
    try {
      const res = await createLab({ name: labName, category: category || 'general' })
      const labs = await getLabs()
      setLabs(labs.data)
      navigate('/lab/' + res.data.id)
    } catch(e) { alert('Failed to create lab') }
  }
  return (
    <>
      <div style={{ height:48, background:'#161b22', borderBottom:'1px solid #21262d', display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 20px', flexShrink:0 }}>
        <span style={{ fontWeight:600, fontSize:15, color:'#e6edf3' }}>{title}</span>
        <div style={{ display:'flex', gap:8 }}>
          <button onClick={handleNewLab} style={{ background:'#238636', color:'#fff', border:'none', padding:'6px 14px', borderRadius:6, cursor:'pointer', fontSize:13, fontWeight:500 }}>+ New Lab</button>
          <button onClick={()=>navigate('/templates')} style={{ background:'transparent', color:'#8b949e', border:'1px solid #30363d', padding:'6px 14px', borderRadius:6, cursor:'pointer', fontSize:13 }}>Templates</button>
        </div>
      </div>
      
      <PromptModal
        open={showNamePrompt}
        onClose={() => setShowNamePrompt(false)}
        title="Create New Lab"
        message="Enter a name for your lab:"
        placeholder="e.g., OSPF Multi-Area Lab"
        onSubmit={handleNameSubmit}
      />
      
      <PromptModal
        open={showCategoryPrompt}
        onClose={() => setShowCategoryPrompt(false)}
        title="Lab Category"
        message="Choose a category (or leave blank for 'general'):"
        placeholder="security, devops, ai-ml, networking, general"
        defaultValue="general"
        onSubmit={handleCategorySubmit}
      />
    </>
  )
}
