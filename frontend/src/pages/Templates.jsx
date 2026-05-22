import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTemplates, getCategories, deployTemplate, getLabs } from '../utils/api'
import { useStore } from '../store'
const CM = { security:{icon:'🔒',color:'#f85149',bg:'#2d1b1b',border:'#f85149'}, devops:{icon:'⚙️',color:'#3fb950',bg:'#1b2d1b',border:'#3fb950'}, 'ai-ml':{icon:'🤖',color:'#a371f7',bg:'#2d1b3d',border:'#a371f7'}, networking:{icon:'🌐',color:'#58a6ff',bg:'#1b2535',border:'#58a6ff'} }
const DC = { beginner:'#3fb950', intermediate:'#e3b341', advanced:'#f85149' }
export default function Templates() {
  const navigate = useNavigate()
  const { templates, setTemplates, setLabs } = useStore()
  const [categories, setCategories] = useState([])
  const [active, setActive] = useState('all')
  const [deploying, setDeploying] = useState(null)
  useEffect(() => {
    getTemplates().then(r=>setTemplates(r.data)).catch(()=>{})
    getCategories().then(r=>setCategories(r.data)).catch(()=>{})
  }, [])
  const filtered = active==='all' ? templates : templates.filter(t=>t.category===active)
  const handleDeploy = async (tpl) => {
    setDeploying(tpl.id)
    try {
      const res = await deployTemplate(tpl.id, tpl.name)
      const labs = await getLabs()
      setLabs(labs.data)
      navigate('/lab/'+res.data.lab_id)
    } catch(e) { alert('Deploy failed') }
    setDeploying(null)
  }
  return (
    <div style={{ padding:24 }}>
      <div style={{ marginBottom:20, display:'flex', gap:8, flexWrap:'wrap' }}>
        <button onClick={()=>setActive('all')} style={{ padding:'6px 14px', borderRadius:20, border:'1px solid', cursor:'pointer', fontSize:13, background:active==='all'?'#21262d':'transparent', borderColor:active==='all'?'#58a6ff':'#30363d', color:active==='all'?'#58a6ff':'#8b949e' }}>All ({templates.length})</button>
        {categories.map(cat => {
          const m = CM[cat.name]||{}
          return <button key={cat.name} onClick={()=>setActive(cat.name)} style={{ padding:'6px 14px', borderRadius:20, border:'1px solid', cursor:'pointer', fontSize:13, background:active===cat.name?m.bg:'transparent', borderColor:active===cat.name?m.border:'#30363d', color:active===cat.name?m.color:'#8b949e' }}>{m.icon} {cat.name} ({cat.count})</button>
        })}
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))', gap:16 }}>
        {filtered.map(tpl => {
          const m = CM[tpl.category]||{icon:'🧪',color:'#8b949e',bg:'#21262d',border:'#30363d'}
          return (
            <div key={tpl.id} style={{ background:'#161b22', border:'1px solid #21262d', borderTop:'3px solid '+m.border, borderRadius:10, padding:16, display:'flex', flexDirection:'column', gap:10 }}>
              <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:4 }}>
                <span style={{ fontSize:20 }}>{m.icon}</span>
                <span style={{ fontSize:14, fontWeight:600, color:'#e6edf3' }}>{tpl.name}</span>
              </div>
              <div style={{ fontSize:12, color:'#8b949e' }}>{tpl.description}</div>
              <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
                <span style={{ fontSize:11, padding:'2px 7px', background:'#21262d', borderRadius:12, color:m.color }}>{tpl.category}</span>
                <span style={{ fontSize:11, padding:'2px 7px', background:'#21262d', borderRadius:12, color:DC[tpl.difficulty]||'#8b949e' }}>{tpl.difficulty}</span>
                <span style={{ fontSize:11, padding:'2px 7px', background:'#21262d', borderRadius:12, color:'#8b949e' }}>{tpl.nodes?.length||0} nodes</span>
              </div>
              <div style={{ display:'flex', gap:4, flexWrap:'wrap' }}>
                {(tpl.nodes||[]).slice(0,4).map(n=>(
                  <span key={n.name} style={{ fontSize:10, padding:'1px 6px', background:'#21262d', borderRadius:4, color:n.type==='docker'?'#3fb950':'#58a6ff' }}>{n.type==='docker'?'🐳':'💻'} {n.name}</span>
                ))}
                {(tpl.nodes?.length||0)>4&&<span style={{ fontSize:10, padding:'1px 6px', background:'#21262d', borderRadius:4, color:'#8b949e' }}>+{tpl.nodes.length-4} more</span>}
              </div>
              <button onClick={()=>handleDeploy(tpl)} disabled={deploying===tpl.id} style={{ background:m.bg, border:'1px solid '+m.border, color:m.color, padding:'8px', borderRadius:6, cursor:'pointer', fontSize:13, fontWeight:500, marginTop:'auto' }}>
                {deploying===tpl.id?'Deploying...':'▶ Deploy Lab'}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
