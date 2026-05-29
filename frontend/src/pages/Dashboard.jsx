import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getLabs } from '../utils/api'
import { useStore } from '../store'
import AIBuilderPanel from '../components/AIBuilder/AIBuilderPanel'

const TEMPLATES = [
  { id:'wazuh-soc',   name:'Wazuh SOC Lab',  desc:'SIEM + threat detection', color:'#dc2626' },
  { id:'pentest-lab',   name:'Pentest Lab',     desc:'Kali + Metasploit',       color:'#9333ea' },
  { id:'kubernetes-cluster',   name:'Kubernetes',      desc:'K8s cluster lab',          color:'#16a34a' },
  { id:'llm-sandbox',   name:'LLM Security',    desc:'AI/LLM pentesting',       color:'#7c3aed' },
  { id:'ansible-lab',   name:'Ansible',         desc:'Automation practice',      color:'#15803d' },
  { id:'vyos-routing',  name:'VyOS Routing',    desc:'BGP/OSPF lab',            color:'#0369a1' },
]

const CAT_COLORS = {
  security:'#f85149', devops:'#3fb950',
  'ai-ml':'#a371f7', networking:'#58a6ff', general:'#8b949e'
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { labs, setLabs } = useStore()
  const [loading, setLoading] = useState(true)
  const [dismissed, setDismissed] = useState(new Set())
  const [aiOpen, setAiOpen] = useState(false)

  useEffect(() => {
    getLabs()
      .then(r => { setLabs(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  // × just hides the lab card from dashboard view — does NOT delete
  const dismissLab = (e, labId) => {
    e.stopPropagation()
    setDismissed(prev => new Set([...prev, labId]))
  }

  const safeLabs = (Array.isArray(labs) ? labs : []).filter(l => !dismissed.has(l.id))

  return (
    <div style={{ padding:28, overflowY:'auto', height:'100%', boxSizing:'border-box', fontFamily:'system-ui,sans-serif' }}>

      {/* CRE-46 — Build with AI banner */}
      <div style={{ display:'flex', alignItems:'center', gap:16, marginBottom:24,
        background:'linear-gradient(90deg,#1b1235,#161b22)', border:'1px solid #30363d',
        borderRadius:12, padding:'18px 22px' }}>
        <div style={{ flex:1 }}>
          <div style={{ fontSize:15, fontWeight:700, color:'#e6edf3' }}>✨ Build a lab with AI</div>
          <div style={{ fontSize:12, color:'#8b949e', marginTop:4 }}>
            Describe the network you want in plain English — the AI assembles nodes, links and configs for you.
          </div>
        </div>
        <button onClick={() => setAiOpen(true)}
          style={{ background:'#8957e5', border:'1px solid #a371f7', borderRadius:8,
            color:'#fff', fontSize:13, fontWeight:600, padding:'10px 18px', cursor:'pointer',
            whiteSpace:'nowrap' }}
          onMouseEnter={e => e.currentTarget.style.background='#9a6cf0'}
          onMouseLeave={e => e.currentTarget.style.background='#8957e5'}>
          ✨ Build with AI
        </button>
      </div>

      <AIBuilderPanel open={aiOpen} onClose={() => setAiOpen(false)} />

      {/* Stats */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:16, marginBottom:28 }}>
        {[
          { label:'Total Labs',  val: safeLabs.length,                                    color:'#58a6ff' },
          { label:'Security',    val: safeLabs.filter(l=>l.category==='security').length,  color:'#f85149' },
          { label:'DevOps',      val: safeLabs.filter(l=>l.category==='devops').length,    color:'#3fb950' },
          { label:'AI/ML',       val: safeLabs.filter(l=>l.category==='ai-ml').length,     color:'#a371f7' },
        ].map(stat => (
          <div key={stat.label} style={{ background:'#161b22', border:'1px solid #21262d', borderRadius:10, padding:'18px 20px' }}>
            <div style={{ fontSize:12, color:'#8b949e', marginBottom:8 }}>{stat.label}</div>
            <div style={{ fontSize:28, fontWeight:700, color:stat.color }}>{stat.val}</div>
          </div>
        ))}
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:24 }}>

        {/* My Labs */}
        <div>
          <div style={{ fontSize:14, fontWeight:600, color:'#e6edf3', marginBottom:14 }}>My Labs</div>
          <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
            {loading && <div style={{ color:'#8b949e', fontSize:13 }}>Loading...</div>}
            {!loading && safeLabs.length === 0 && (
              <div style={{ color:'#484f58', fontSize:13, padding:16, border:'1px dashed #21262d', borderRadius:8, textAlign:'center' }}>
                No labs yet — use + New Lab or create one from a template.
              </div>
            )}
            {safeLabs.map(lab => (
              <div key={lab.id} onClick={() => navigate('/lab/'+lab.id)}
                style={{ background:'#161b22', border:'1px solid #21262d', borderRadius:8, padding:'14px 16px',
                  cursor:'pointer', display:'flex', alignItems:'center', gap:12 }}
                onMouseEnter={e => e.currentTarget.style.borderColor='#30363d'}
                onMouseLeave={e => e.currentTarget.style.borderColor='#21262d'}>

                <div style={{ width:8, height:8, borderRadius:'50%',
                  background: CAT_COLORS[lab.category]||'#8b949e', flexShrink:0 }}/>

                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ fontSize:13, fontWeight:500, color:'#e6edf3',
                    overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                    {lab.name}
                  </div>
                  <div style={{ fontSize:11, color:'#8b949e', marginTop:2 }}>{lab.category||'general'}</div>
                </div>

                <div style={{ fontSize:11, padding:'2px 8px', borderRadius:12,
                  background: lab.status==='running'?'#1a3a2a':'#1c1c1c',
                  color: lab.status==='running'?'#3fb950':'#8b949e',
                  border:'1px solid '+(lab.status==='running'?'#3fb95033':'#21262d') }}>
                  {lab.status||'stopped'}
                </div>

                {/* × = dismiss from dashboard view only, lab is NOT deleted */}
                <button
                  onClick={e => dismissLab(e, lab.id)}
                  title="Hide from dashboard (lab still exists in sidebar)"
                  style={{ background:'transparent', border:'none', color:'#484f58',
                    cursor:'pointer', fontSize:16, padding:'0 4px', lineHeight:1, flexShrink:0 }}
                  onMouseEnter={e => e.currentTarget.style.color='#8b949e'}
                  onMouseLeave={e => e.currentTarget.style.color='#484f58'}>
                  ×
                </button>
              </div>
            ))}

            {dismissed.size > 0 && (
              <button onClick={() => setDismissed(new Set())}
                style={{ marginTop:4, background:'transparent', border:'none',
                  color:'#484f58', cursor:'pointer', fontSize:11, textAlign:'left', padding:'2px 0' }}
                onMouseEnter={e => e.currentTarget.style.color='#8b949e'}
                onMouseLeave={e => e.currentTarget.style.color='#484f58'}>
                ↻ Show {dismissed.size} hidden lab{dismissed.size>1?'s':''}
              </button>
            )}
          </div>
        </div>

        {/* Quick Deploy */}
        <div>
          <div style={{ fontSize:14, fontWeight:600, color:'#e6edf3', marginBottom:14 }}>Quick Deploy</div>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8 }}>
            {TEMPLATES.map(t => (
              <div key={t.id}
              onClick={async () => {
                const r = await fetch('/api/templates/' + t.id + '/deploy', {method:'POST'})
                if (r.ok) {
                  const lab = await r.json()
                  navigate('/lab/' + lab.lab_id)
                }
              }}
                style={{ background:t.color+'18', border:'1px solid '+t.color+'44',
                  borderRadius:8, padding:'14px 16px', cursor:'pointer' }}
                onMouseEnter={e => { e.currentTarget.style.background=t.color+'28'; e.currentTarget.style.borderColor=t.color+'88' }}
                onMouseLeave={e => { e.currentTarget.style.background=t.color+'18'; e.currentTarget.style.borderColor=t.color+'44' }}>
                <div style={{ fontSize:13, fontWeight:600, color:'#e6edf3', marginBottom:3 }}>{t.name}</div>
                <div style={{ fontSize:11, color:'#8b949e' }}>{t.desc}</div>
              </div>
            ))}
          </div>
          <div onClick={() => navigate('/templates')}
            style={{ marginTop:8, padding:10, background:'#161b22', border:'1px solid #21262d',
              borderRadius:8, textAlign:'center', fontSize:13, color:'#8b949e', cursor:'pointer' }}
            onMouseEnter={e => e.currentTarget.style.color='#e6edf3'}
            onMouseLeave={e => e.currentTarget.style.color='#8b949e'}>
            View all templates →
          </div>
        </div>
      </div>
    </div>
  )
}
