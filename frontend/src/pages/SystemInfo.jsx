import React, { useEffect } from 'react'
import { useStore } from '../store'
import { getSystemInfo } from '../utils/api'
export default function SystemInfo() {
  const { systemInfo, setSystemInfo } = useStore()
  useEffect(() => { getSystemInfo().then(r=>setSystemInfo(r.data)).catch(()=>{}) }, [])
  const info = systemInfo || {}
  const CHECKS = [
    { label:'KVM / Hardware Virtualization', value:info.kvm_available },
    { label:'QEMU Binary', value:info.qemu_available },
    { label:'Docker Engine', value:info.docker_available },
    { label:'Open vSwitch', value:info.ovs_available },
  ]
  return (
    <div style={{ padding:24, maxWidth:800 }}>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:12, marginBottom:24 }}>
        {[['Platform',info.platform||'—'],['Architecture',info.arch||'—'],['License',info.tier||'free'],['Disk Free',info.disk_free_gb?info.disk_free_gb+' GB':'—'],['Disk Total',info.disk_total_gb?info.disk_total_gb+' GB':'—'],['Version','1.0.0']].map(([l,v])=>(
          <div key={l} style={{ background:'#161b22', border:'1px solid #21262d', borderRadius:10, padding:'14px 16px' }}>
            <div style={{ fontSize:12, color:'#8b949e', marginBottom:4 }}>{l}</div>
            <div style={{ fontSize:18, fontWeight:600, color:'#e6edf3' }}>{v}</div>
          </div>
        ))}
      </div>
      <div style={{ background:'#161b22', border:'1px solid #21262d', borderRadius:10, padding:16, marginBottom:16 }}>
        <div style={{ fontSize:14, fontWeight:600, color:'#e6edf3', marginBottom:12 }}>System Capabilities</div>
        <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
          {CHECKS.map(c=>(
            <div key={c.label} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding:'8px 12px', background:'#21262d', borderRadius:6 }}>
              <span style={{ fontSize:13, color:'#e6edf3' }}>{c.label}</span>
              <span style={{ fontSize:12, padding:'2px 10px', borderRadius:12, background:c.value?'#1a3a1a':'#2d1b1b', color:c.value?'#3fb950':'#f85149' }}>
                {c.value===undefined?'checking...':c.value?'✓ available':'✗ not found'}
              </span>
            </div>
          ))}
        </div>
      </div>
      <div style={{ background:'#161b22', border:'1px solid #21262d', borderRadius:10, padding:16 }}>
        <div style={{ fontSize:14, fontWeight:600, color:'#e6edf3', marginBottom:12 }}>Storage Paths</div>
        {[['Images',info.images_dir],['Labs',info.labs_dir]].map(([l,p])=>(
          <div key={l} style={{ display:'flex', gap:12, fontSize:13, padding:'6px 0', borderBottom:'1px solid #21262d' }}>
            <span style={{ color:'#8b949e', minWidth:60 }}>{l}</span>
            <span style={{ color:'#58a6ff', fontFamily:'monospace', fontSize:12 }}>{p||'—'}</span>
          </div>
        ))}
        <div style={{ marginTop:12, fontSize:12, color:'#8b949e' }}>Drop .qcow2 or .vmdk images into the images directory.</div>
      </div>
    </div>
  )
}
