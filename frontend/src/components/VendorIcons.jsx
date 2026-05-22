import React from 'react'

export const VENDORS = {
  // ── CISCO ────────────────────────────────────────────────
  'cisco-router':    { label:'Cisco Router',     vendor:'Cisco',    category:'Routers',    color:'#1d4ed8', shape:'router',    ifaces:['GigabitEthernet0/0','GigabitEthernet0/1','GigabitEthernet0/2','GigabitEthernet0/3'] },
  'cisco-switch':    { label:'Cisco Switch',     vendor:'Cisco',    category:'Switches',   color:'#1d4ed8', shape:'switch_l2', ifaces:['GigabitEthernet0/1','GigabitEthernet0/2','GigabitEthernet0/3','GigabitEthernet0/4','GigabitEthernet0/5','GigabitEthernet0/6'] },
  'cisco-l3switch':  { label:'Cisco L3 Switch',  vendor:'Cisco',    category:'Switches',   color:'#1d4ed8', shape:'switch_l3', ifaces:['GigabitEthernet0/1','GigabitEthernet0/2','GigabitEthernet0/3','GigabitEthernet0/4'] },
  'cisco-firewall':  { label:'Cisco ASA',        vendor:'Cisco',    category:'Firewalls',  color:'#1d4ed8', shape:'firewall',  ifaces:['GigabitEthernet0/0','GigabitEthernet0/1','GigabitEthernet0/2','Management0/0'] },
  'cisco-asa':       { label:'Cisco ASAv',       vendor:'Cisco',    category:'Firewalls',  color:'#1d4ed8', shape:'firewall',  ifaces:['GigabitEthernet0/0','GigabitEthernet0/1','GigabitEthernet0/2','Management0/0'] },
  'cisco-csr':       { label:'Cisco CSRv1000',   vendor:'Cisco',    category:'Routers',    color:'#1d4ed8', shape:'router',    ifaces:['GigabitEthernet1','GigabitEthernet2','GigabitEthernet3','GigabitEthernet4'] },
  'cisco-vios':      { label:'Cisco vIOS',       vendor:'Cisco',    category:'Routers',    color:'#1d4ed8', shape:'router',    ifaces:['GigabitEthernet0/0','GigabitEthernet0/1','GigabitEthernet0/2','GigabitEthernet0/3'] },
  'cisco-nxos':      { label:'Cisco NX-OS',      vendor:'Cisco',    category:'Switches',   color:'#1d4ed8', shape:'switch_l3', ifaces:['Ethernet1/1','Ethernet1/2','Ethernet1/3','Ethernet1/4','mgmt0'] },
  'cisco-xrv':       { label:'Cisco XRv',        vendor:'Cisco',    category:'Routers',    color:'#1d4ed8', shape:'router',    ifaces:['GigabitEthernet0/0/0/0','GigabitEthernet0/0/0/1','MgmtEth0/0/CPU0/0'] },

  // ── JUNIPER ──────────────────────────────────────────────
  'juniper-vmx':     { label:'Juniper vMX',      vendor:'Juniper',  category:'Routers',    color:'#16a34a', shape:'router',    ifaces:['ge-0/0/0','ge-0/0/1','ge-0/0/2','ge-0/0/3','fxp0'] },
  'juniper-vsrx':    { label:'Juniper vSRX',     vendor:'Juniper',  category:'Firewalls',  color:'#16a34a', shape:'firewall',  ifaces:['ge-0/0/0','ge-0/0/1','ge-0/0/2','fxp0'] },
  'juniper-vqfx':    { label:'Juniper vQFX',     vendor:'Juniper',  category:'Switches',   color:'#16a34a', shape:'switch_l3', ifaces:['xe-0/0/0','xe-0/0/1','xe-0/0/2','xe-0/0/3','em0'] },
  'juniper-vevo':    { label:'Juniper vJunos',   vendor:'Juniper',  category:'Routers',    color:'#16a34a', shape:'router',    ifaces:['et-0/0/0','et-0/0/1','fxp0'] },

  // ── PALO ALTO ────────────────────────────────────────────
  'paloalto-fw':     { label:'Palo Alto VM',     vendor:'PaloAlto', category:'Firewalls',  color:'#dc2626', shape:'firewall',  ifaces:['ethernet1/1','ethernet1/2','ethernet1/3','ethernet1/4','management'] },
  'paloalto-panorama':{ label:'Panorama',        vendor:'PaloAlto', category:'Management', color:'#dc2626', shape:'server',    ifaces:['Management','Ethernet1','Ethernet2'] },

  // ── FORTINET ─────────────────────────────────────────────
  'fortinet-fw':     { label:'FortiGate',        vendor:'Fortinet', category:'Firewalls',  color:'#ea580c', shape:'firewall',  ifaces:['port1','port2','port3','port4'] },
  'fortinet-ap':     { label:'FortiAP',          vendor:'Fortinet', category:'Wireless',   color:'#ea580c', shape:'wireless',  ifaces:['port1','port2'] },

  // ── ARISTA ───────────────────────────────────────────────
  'arista-eos':      { label:'Arista vEOS',      vendor:'Arista',   category:'Switches',   color:'#7c3aed', shape:'switch_l3', ifaces:['Ethernet1','Ethernet2','Ethernet3','Ethernet4','Management1'] },
  'arista-ceos':     { label:'Arista cEOS',      vendor:'Arista',   category:'Switches',   color:'#7c3aed', shape:'switch_l3', ifaces:['Ethernet1','Ethernet2','Ethernet3','Ethernet4','Management0'] },


  // ── ARUBA / HPE ──────────────────────────────────────────
  'aruba-cx':        { label:'ArubaOS-CX',      vendor:'Aruba',    category:'Switches',   color:'#f97316', shape:'switch_l3', ifaces:['1/1/1','1/1/2','1/1/3','1/1/4','1/1/5','1/1/6','mgmt'] },
  'aruba-ap':        { label:'Aruba AP',         vendor:'Aruba',    category:'Wireless',   color:'#f97316', shape:'wireless',  ifaces:['eth0','eth1'] },

  // ── VYOS / PFSENSE / OPNSENSE ────────────────────────────
  'vyos':            { label:'VyOS Router',      vendor:'VyOS',     category:'Routers',    color:'#0369a1', shape:'router',    ifaces:['eth0','eth1','eth2','eth3'] },
  'pfsense':         { label:'pfSense',          vendor:'pfSense',  category:'Firewalls',  color:'#b45309', shape:'firewall',  ifaces:['em0','em1','em2','em3'] },
  'opnsense':        { label:'OPNsense',         vendor:'OPNsense', category:'Firewalls',  color:'#b45309', shape:'firewall',  ifaces:['em0','em1','em2','em3'] },

  // ── LINUX ────────────────────────────────────────────────
  'linux-server':    { label:'Linux Server',     vendor:'Linux',    category:'Servers',    color:'#15803d', shape:'server',    ifaces:['eth0','eth1','eth2','mgmt'] },
  'linux-desktop':   { label:'Linux Desktop',   vendor:'Linux',    category:'Servers',    color:'#15803d', shape:'desktop',   ifaces:['eth0','eth1'] },
  'ubuntu':          { label:'Ubuntu Server',   vendor:'Linux',    category:'Servers',    color:'#e05300', shape:'server',    ifaces:['ens3','ens4','ens5'] },
  'kali':            { label:'Kali Linux',      vendor:'Kali',     category:'Security',   color:'#1a1a2e', shape:'kali',      ifaces:['eth0','eth1'] },
  'windows-server':  { label:'Windows Server',  vendor:'Microsoft',category:'Servers',    color:'#0078d4', shape:'server',    ifaces:['Ethernet0','Ethernet1'] },
  'windows-desktop': { label:'Windows PC',      vendor:'Microsoft',category:'Servers',    color:'#0078d4', shape:'desktop',   ifaces:['Ethernet0'] },

  // ── SECURITY / SIEM ──────────────────────────────────────
  'wazuh':           { label:'Wazuh SIEM',      vendor:'Wazuh',    category:'Security',   color:'#0c4a6e', shape:'server',    ifaces:['eth0','eth1'] },
  'suricata':        { label:'Suricata IDS',    vendor:'OISF',     category:'Security',   color:'#0891b2', shape:'server',    ifaces:['eth0','eth1'] },
  'zeek':            { label:'Zeek Monitor',    vendor:'Zeek',     category:'Security',   color:'#0369a1', shape:'server',    ifaces:['eth0','eth1'] },
  'thehive':         { label:'TheHive',         vendor:'TheHive',  category:'Security',   color:'#7c3aed', shape:'server',    ifaces:['eth0'] },
  'caldera':         { label:'MITRE Caldera',   vendor:'MITRE',    category:'Security',   color:'#b91c1c', shape:'server',    ifaces:['eth0'] },

  // ── DEVOPS / CLOUD ───────────────────────────────────────
  'k8s-node':        { label:'Kubernetes Node', vendor:'K8s',      category:'DevOps',     color:'#3b82f6', shape:'server',    ifaces:['eth0','eth1'] },
  'docker-host':     { label:'Docker Host',     vendor:'Docker',   category:'DevOps',     color:'#0369a1', shape:'server',    ifaces:['eth0','docker0'] },
  'ansible':         { label:'Ansible',         vendor:'RedHat',   category:'DevOps',     color:'#dc2626', shape:'server',    ifaces:['eth0'] },
  'jenkins':         { label:'Jenkins',         vendor:'Jenkins',  category:'DevOps',     color:'#d97706', shape:'server',    ifaces:['eth0'] },

  // ── AI / ML ──────────────────────────────────────────────
  'ollama':          { label:'Ollama LLM',      vendor:'Ollama',   category:'AI/ML',      color:'#92400e', shape:'server',    ifaces:['eth0'] },
  'jupyter':         { label:'Jupyter',         vendor:'Jupyter',  category:'AI/ML',      color:'#f59e0b', shape:'server',    ifaces:['eth0'] },

  // ── GENERIC ──────────────────────────────────────────────
  'generic-router':  { label:'Router',          vendor:'Generic',  category:'Generic',    color:'#6b7280', shape:'router',    ifaces:['eth0','eth1','eth2','eth3'] },
  'generic-switch':  { label:'Switch',          vendor:'Generic',  category:'Generic',    color:'#6b7280', shape:'switch_l2', ifaces:['eth0','eth1','eth2','eth3','eth4','eth5'] },
  'generic-server':  { label:'Server',          vendor:'Generic',  category:'Generic',    color:'#6b7280', shape:'server',    ifaces:['eth0','eth1'] },
  'generic-pc':      { label:'PC/Workstation',  vendor:'Generic',  category:'Generic',    color:'#6b7280', shape:'desktop',   ifaces:['eth0'] },
}

export const VENDOR_CATEGORIES = [...new Set(Object.values(VENDORS).map(v=>v.category))]
export const VENDOR_GROUPS = VENDOR_CATEGORIES.reduce((acc,cat)=>{
  acc[cat] = Object.entries(VENDORS).filter(([,v])=>v.category===cat)
  return acc
},{})

export function NodeIcon({ type, color, size=48, muted=false }) {
  const def = VENDORS[type] || VENDORS['generic-router']
  const c = muted ? '#9ca3af' : (color || def.color)
  const s = size
  const hw = s/2

  const shapes = {
    router: (
      <g>
        <circle cx={hw} cy={hw} r={hw-2} fill="none" stroke={c} strokeWidth="2.5"/>
        <circle cx={hw} cy={hw} r={s/7} fill="none" stroke={c} strokeWidth="2"/>
        <line x1={hw} y1="2" x2={hw} y2={s*0.35} stroke={c} strokeWidth="2.5"/>
        <line x1={hw} y1={s*0.65} x2={hw} y2={s-2} stroke={c} strokeWidth="2.5"/>
        <line x1="2" y1={hw} x2={s*0.35} y2={hw} stroke={c} strokeWidth="2.5"/>
        <line x1={s*0.65} y1={hw} x2={s-2} y2={hw} stroke={c} strokeWidth="2.5"/>
        <line x1={s*0.2} y1={s*0.2} x2={s*0.33} y2={s*0.33} stroke={c} strokeWidth="2"/>
        <line x1={s*0.67} y1={s*0.2} x2={s*0.8} y2={s*0.33} stroke={c} strokeWidth="2"/>
        <line x1={s*0.2} y1={s*0.8} x2={s*0.33} y2={s*0.67} stroke={c} strokeWidth="2"/>
        <line x1={s*0.67} y1={s*0.8} x2={s*0.8} y2={s*0.67} stroke={c} strokeWidth="2"/>
      </g>
    ),
    switch_l2: (
      <g>
        <rect x="3" y={s*0.3} width={s-6} height={s*0.4} rx="4" fill="none" stroke={c} strokeWidth="2.5"/>
        {[s*0.2,s*0.36,s*0.52,s*0.68,s*0.84].map((x,i)=>(
          <g key={i}>
            <line x1={x} y1={s*0.3} x2={x} y2={s*0.7} stroke={c} strokeWidth="1.5"/>
            <line x1={x} y1={s*0.2} x2={x} y2={s*0.3} stroke={c} strokeWidth="2.5"/>
            <circle cx={x} cy={s*0.18} r="2.5" fill={muted?'#9ca3af':c}/>
          </g>
        ))}
        <rect x={s*0.82} y={s*0.38} width={s*0.12} height={s*0.1} rx="1" fill={c} opacity="0.7"/>
      </g>
    ),
    switch_l3: (
      <g>
        <rect x="3" y={s*0.25} width={s-6} height={s*0.5} rx="4" fill="none" stroke={c} strokeWidth="2.5"/>
        {[s*0.2,s*0.36,s*0.52,s*0.68,s*0.84].map((x,i)=>(
          <g key={i}>
            <line x1={x} y1={s*0.25} x2={x} y2={s*0.75} stroke={c} strokeWidth="1.5"/>
            <line x1={x} y1={s*0.14} x2={x} y2={s*0.25} stroke={c} strokeWidth="2.5"/>
            <circle cx={x} cy={s*0.12} r="2.5" fill={muted?'#9ca3af':c}/>
          </g>
        ))}
        <text x={hw} y={s*0.62} textAnchor="middle" fontSize={s*0.16} fill={c} fontFamily="monospace" fontWeight="700">L3</text>
      </g>
    ),
    firewall: (
      <g>
        <rect x="4" y="4" width={s-8} height={s-8} rx="3" fill="none" stroke={c} strokeWidth="2.5"/>
        {[s*0.25,s*0.45,s*0.65,s*0.85].map((y,i)=>(
          <line key={i} x1="4" y1={y} x2={s-4} y2={y} stroke={c} strokeWidth={i%2===0?2:1.5}/>
        ))}
        {[s*0.28,s*0.48,s*0.68].map((x,i)=>(
          <line key={i} x1={x} y1="4" x2={x} y2={s-4} stroke={c} strokeWidth="1.5"/>
        ))}
        <rect x={s*0.65} y={s*0.08} width={s*0.22} height={s*0.14} rx="2" fill={c} opacity="0.8"/>
      </g>
    ),
    server: (
      <g>
        <rect x="4" y="4" width={s-8} height={s-8} rx="3" fill="none" stroke={c} strokeWidth="2.5"/>
        {[s*0.25,s*0.42,s*0.59,s*0.76].map((y,i)=>(
          <g key={i}>
            <rect x="8" y={y-s*0.07} width={s-16} height={s*0.13} rx="2" fill="none" stroke={c} strokeWidth="1.5"/>
            <circle cx={s-14} cy={y} r="3" fill={muted?'#9ca3af':i===0?'#22c55e':c} opacity={i===0?1:0.5}/>
            <rect x="10" y={y-s*0.04} width={s*0.28} height={s*0.07} rx="1" fill={c} opacity="0.3"/>
          </g>
        ))}
      </g>
    ),
    desktop: (
      <g>
        <rect x="4" y="4" width={s-8} height={s*0.6} rx="3" fill="none" stroke={c} strokeWidth="2.5"/>
        <line x1="4" y1={s*0.64} x2={s-4} y2={s*0.64} stroke={c} strokeWidth="1.5"/>
        <rect x={hw-s*0.15} y={s*0.64} width={s*0.3} height={s*0.14} fill="none" stroke={c} strokeWidth="1.5"/>
        <line x1={s*0.3} y1={s*0.78} x2={s*0.7} y2={s*0.78} stroke={c} strokeWidth="2.5"/>
        <line x1={hw-s*0.18} y1={s*0.2} x2={hw+s*0.18} y2={s*0.2} stroke={c} strokeWidth="1.5"/>
        <line x1={hw-s*0.18} y1={s*0.33} x2={hw+s*0.08} y2={s*0.33} stroke={c} strokeWidth="1.5"/>
        <line x1={hw-s*0.18} y1={s*0.46} x2={hw+s*0.14} y2={s*0.46} stroke={c} strokeWidth="1.5"/>
      </g>
    ),
    kali: (
      <g>
        <rect x="4" y="4" width={s-8} height={s*0.6} rx="3" fill="none" stroke={c} strokeWidth="2.5"/>
        <line x1="4" y1={s*0.64} x2={s-4} y2={s*0.64} stroke={c} strokeWidth="1.5"/>
        <rect x={hw-s*0.15} y={s*0.64} width={s*0.3} height={s*0.14} fill="none" stroke={c} strokeWidth="1.5"/>
        <line x1={s*0.3} y1={s*0.78} x2={s*0.7} y2={s*0.78} stroke={c} strokeWidth="2.5"/>
        <path d={`M${hw} ${s*0.12} L${hw+s*0.2} ${s*0.48} L${hw-s*0.2} ${s*0.48} Z`} fill="none" stroke={c} strokeWidth="2"/>
        <circle cx={hw} cy={s*0.3} r={s*0.06} fill={c}/>
      </g>
    ),
    wireless: (
      <g>
        <circle cx={hw} cy={s*0.65} r={s*0.12} fill="none" stroke={c} strokeWidth="2.5"/>
        {[s*0.22,s*0.3,s*0.38].map((r2,i)=>(
          <path key={i} d={`M${hw-r2} ${s*0.5} Q${hw} ${s*0.5-r2} ${hw+r2} ${s*0.5}`} fill="none" stroke={c} strokeWidth="2" opacity={1-i*0.25}/>
        ))}
        <line x1={hw} y1={s*0.53} x2={hw} y2={s*0.65} stroke={c} strokeWidth="2"/>
      </g>
    ),
  }

  const shape = def.shape || 'server'
  return (
    <svg width={s} height={s} viewBox={`0 0 ${s} ${s}`} style={{overflow:'visible'}}>
      {shapes[shape] || shapes.server}
    </svg>
  )
}

export function VendorBadge({ vendor, size=10 }) {
  const colors = {
    Cisco:'#1d4ed8', Juniper:'#16a34a', PaloAlto:'#dc2626',
    Fortinet:'#ea580c', Arista:'#7c3aed', VyOS:'#0369a1',
    pfSense:'#b45309', OPNsense:'#b45309', Linux:'#15803d',
    Kali:'#1a1a2e', Microsoft:'#0078d4', Wazuh:'#0c4a6e',
    Generic:'#6b7280', Aruba:'#f97316', K8s:'#3b82f6', Docker:'#0369a1',
    RedHat:'#dc2626', Ollama:'#92400e',
  }
  const bg = colors[vendor] || '#6b7280'
  return (
    <span style={{fontSize:size,padding:'1px 4px',borderRadius:2,background:bg+'22',color:bg,fontWeight:600,fontFamily:'monospace',border:`1px solid ${bg}44`}}>
      {vendor}
    </span>
  )
}
