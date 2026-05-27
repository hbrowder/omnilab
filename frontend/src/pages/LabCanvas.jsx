import React, { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getTopology, getLab, addNode, deleteNode, getTextObjects, createTextObject, updateTextObject, deleteTextObject } from '../utils/api'
import { useStore } from '../store'
import { VENDORS, VENDOR_GROUPS, NodeIcon, VendorBadge } from '../components/VendorIcons'
import NodePanel from '../components/NodePanel'
import DrawingToolbar from '../components/DrawingToolbar'
import TrafficFilterPanel from '../components/TrafficFilterPanel'
import LinkAnimationEngine from '../components/LinkAnimationEngine'
import { useTrafficWebSocket } from '../hooks/useTrafficWebSocket'

const IFACES = ['GigabitEthernet0/0','GigabitEthernet0/1','GigabitEthernet0/2','GigabitEthernet0/3','FastEthernet0/0','FastEthernet0/1','eth0','eth1','eth2','eth3','mgmt0','Loopback0']
const NET_DEFS = {
  bridge:   { label:'Bridge',    color:'#7c3aed' },
  nat:      { label:'NAT/Cloud', color:'#0f766e' },
  internal: { label:'Internal',  color:'#b45309' },
}

const guessType=(n)=>{
  const img=(n.image||'').toLowerCase()
  const name=(n.name||'').toLowerCase()
  const both=img+' '+name
  // Security
  if(both.includes('kali'))return 'kali'
  if(both.includes('wazuh'))return 'wazuh'
  if(both.includes('suricata'))return 'suricata'
  if(both.includes('zeek'))return 'zeek'
  if(both.includes('thehive'))return 'thehive'
  if(both.includes('caldera'))return 'caldera'
  // AI/ML
  if(both.includes('ollama'))return 'ollama'
  if(both.includes('jupyter'))return 'jupyter'
  // DevOps
  if(both.includes('k8s')||both.includes('kube'))return 'k8s-node'
  if(both.includes('jenkins'))return 'jenkins'
  if(both.includes('ansible'))return 'ansible'
  if(both.includes('docker')&&!both.includes('cisco'))return 'docker-host'
  // Open source FW/Router
  if(both.includes('pfsense'))return 'pfsense'
  if(both.includes('opnsense'))return 'opnsense'
  if(both.includes('vyos'))return 'vyos'
  // Fortinet
  if(both.includes('forti'))return 'fortinet-fw'
  // Palo Alto
  if(both.includes('palo')||both.includes('panorama'))return 'paloalto-fw'
  // Juniper
  if(both.includes('vsrx'))return 'juniper-vsrx'
  if(both.includes('vqfx'))return 'juniper-vqfx'
  if(both.includes('vmx')||both.includes('juniper'))return 'juniper-vmx'
  // Aruba
  if(both.includes('aruba')||both.includes('aoscx')||both.includes('aos-cx'))return 'aruba-cx'
  // Arista
  if(both.includes('arista')||both.includes('ceos')||both.includes('veos'))return 'arista-eos'
  // Cisco — most specific first
  if(both.includes('nxos')||both.includes('nexus'))return 'cisco-nxos'
  if(both.includes('xrv')||both.includes('iosxr'))return 'cisco-xrv'
  if(both.includes('asa'))return 'cisco-asa'
  if(both.includes('csr'))return 'cisco-csr'
  if(both.includes('vios-l2')||both.includes('iosl2'))return 'cisco-switch'
  if(both.includes('vios')||both.includes('iosvl2'))return 'cisco-router'
  if(both.includes('cisco'))return 'cisco-router'
  // Windows
  if(both.includes('windows')||both.includes('win'))return 'windows-server'
  // Linux types
  if(both.includes('ubuntu'))return 'ubuntu'
  if(both.includes('linux')||both.includes('debian')||both.includes('centos')||both.includes('rhel'))return 'linux-server'
  // Generic by node type
  if(n.type==='qemu')return 'generic-router'
  // Docker default — eth interfaces
  return 'linux-server'
}

export default function LabCanvas() {
  const { labId } = useParams()
  const navigate = useNavigate()
  const { setActiveLab } = useStore()
  const svgRef = useRef(null)

  // ── Use refs for values needed in event handlers to avoid stale closures ──
  const panRef = useRef({x:80,y:40})
  const zoomRef = useRef(1)
  const draggingRef = useRef(null)
  const dragOffsetRef = useRef({x:0,y:0})
  const connectingRef = useRef(null)
  const nodesRef = useRef([])
  const networksRef = useRef([])
  const selectedRef = useRef(new Set())
  const selBoxStart = useRef(null)
  const isPanning = useRef(false)
  const panStart = useRef({x:0,y:0})

  const [nodes, setNodes] = useState([])
  const [networks, setNetworks] = useState([])
  const [links, setLinks] = useState([])
  const [texts, setTexts] = useState([])
  const [labName, setLabName] = useState('')
  const [loading, setLoading] = useState(true)
  const [darkMode, setDarkMode] = useState(false)
  const [hideLabels, setHideLabels] = useState(false)
  const [showMinimap, setShowMinimap] = useState(true)
  const [showTrafficFilters, setShowTrafficFilters] = useState(false) // CRE-68
  const [selBox, setSelBox] = useState(null)
  const [confirmDel, setConfirmDel] = useState(null)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({x:80,y:40})
  const [, forceRender] = useState(0)
  const [connecting, setConnecting] = useState(null)
  const [mousePos, setMousePos] = useState({x:0,y:0})
  const [contextMenu, setContextMenu] = useState(null)
  const [hoveredId, setHoveredId] = useState(null)
  const [selected, setSelected] = useState(()=>new Set())
  // CRE-17: node inspector (right-click → Configure)
  const [selectedNode, setSelectedNode] = useState(null)
  const [ifaceModal, setIfaceModal] = useState(null)
  const [addNodeModal, setAddNodeModal] = useState(null)
  const [addNetModal, setAddNetModal] = useState(null)
  const [qty, setQty] = useState(1)
  const [nodePrefix, setNodePrefix] = useState('')
  const [startNum, setStartNum] = useState(1)
  const [activeCategory, setActiveCategory] = useState('Routers')
  const [pendingAdd, setPendingAdd] = useState(null)
  
  // CRE-64: Drawing tools state
  const [drawingTool, setDrawingTool] = useState('select')
  const [drawFillColor, setDrawFillColor] = useState('rgba(88,166,255,0.3)')
  const [drawStrokeColor, setDrawStrokeColor] = useState('rgba(88,166,255,1)')
  const [drawingShape, setDrawingShape] = useState(null) // {type, startX, startY}

  // CRE-68 Phase 3: WebSocket for real-time traffic animation
  const { connected: wsConnected, events: trafficEvents, packetCounts, activeFilters: wsActiveFilters, lastError: wsLastError } = useTrafficWebSocket(labId)


  // Keep refs in sync with state
  useEffect(()=>{ selectedRef.current=selected },[selected])
  useEffect(()=>{ panRef.current=pan },[pan])
  useEffect(()=>{ zoomRef.current=zoom },[zoom])
  useEffect(()=>{ nodesRef.current=nodes },[nodes])
  useEffect(()=>{ networksRef.current=networks },[networks])
  useEffect(()=>{ connectingRef.current=connecting },[connecting])

  const bg=darkMode?'#0f172a':'#ffffff'
  const gridSm=darkMode?'#1e293b':'#f0f0f0'
  const gridLg=darkMode?'#334155':'#d1d5db'
  const tc=darkMode?'#e2e8f0':'#1e293b'
  const sc=darkMode?'#64748b':'#6b7280'
  const bc=darkMode?'#334155':'#e5e7eb'
  const cb=darkMode?'#1e293b':'#ffffff'
  const cbb=darkMode?'#334155':'#d1d5db'

  useEffect(()=>{
    Promise.all([getLab(labId),getTopology(labId),getTextObjects(labId)]).then(([lr,tr,tor])=>{
      setActiveLab(lr.data)
      setLabName(lr.data.name)
      const topo=tr.data
      setNodes(topo.nodes.map((n,i)=>({
        id:n.id,name:n.name,vendorType:guessType(n),
        x:n.x||120+(i%4)*200,y:n.y||100+Math.floor(i/4)*180,
        status:n.status||'stopped',image:n.image
      })))
      setLinks(topo.links.map(l=>({
        id:l.id,srcId:l.src_node_id,dstId:l.dst_node_id,netId:l.network_id,
        srcIface:l.src_interface||'GigabitEthernet0/0',
        dstIface:l.dst_interface||'eth0',
        color:l.color||null,
        style:l.style||'Solid',
        linkstyle:l.linkstyle||'Straight',
        label:l.label||'',
        labelpos:l.labelpos!=null?l.labelpos:0.5,
        width:l.width||1.5
      })))
      // CRE-64: Load textobjects from API
      setTexts(tor.data.map(obj=>({
        id:obj.id,type:obj.type,x:obj.x,y:obj.y,
        width:obj.width,height:obj.height,
        fill:obj.fill,stroke:obj.stroke,text:obj.text||''
      })))
      setLoading(false)
    }).catch(()=>setLoading(false))
  },[labId])

  // ── Pure ref-based coordinate conversion (no stale closure) ──
  const toCanvas=(clientX,clientY)=>{
    const r=svgRef.current?.getBoundingClientRect()
    if(!r)return{x:0,y:0}
    return{x:(clientX-r.left-panRef.current.x)/zoomRef.current,
           y:(clientY-r.top-panRef.current.y)/zoomRef.current}
  }

  const hitNode=(cx,cy)=>nodesRef.current.find(n=>cx>=n.x-8&&cx<=n.x+56&&cy>=n.y-8&&cy<=n.y+80)
  const hitNet=(cx,cy)=>networksRef.current.find(n=>cx>=n.x-8&&cx<=n.x+68&&cy>=n.y-8&&cy<=n.y+60)

  // ── Global mouse handlers attached to window for reliable drag ──
  useEffect(()=>{
    const onMove=(e)=>{
      const c=toCanvas(e.clientX,e.clientY)
      setMousePos(c)
      
      // CRE-64: Drawing shape - update end coordinates
      if(drawingShape){
        const r=svgRef.current.getBoundingClientRect()
        const cx=(e.clientX-r.left-panRef.current.x)/zoomRef.current
        const cy=(e.clientY-r.top-panRef.current.y)/zoomRef.current
        setDrawingShape(s=>({...s,endX:cx,endY:cy}))
        return
      }
      
      // Drag-select box
      if(selBoxStart.current && !draggingRef.current && !isPanning.current){
        const sx=selBoxStart.current.x, sy=selBoxStart.current.y
        const r=svgRef.current?.getBoundingClientRect()
        if(r){
          const cx2=(e.clientX-r.left-panRef.current.x)/zoomRef.current
          const cy2=(e.clientY-r.top-panRef.current.y)/zoomRef.current
          const box={x:Math.min(sx,cx2),y:Math.min(sy,cy2),w:Math.abs(cx2-sx),h:Math.abs(cy2-sy)}
          setSelBox(box)
          if(box.w>5&&box.h>5){
            const inBox=nodesRef.current.filter(n=>n.x+24>=box.x&&n.x+24<=box.x+box.w&&n.y+24>=box.y&&n.y+24<=box.y+box.h)
            const ns=new Set(inBox.map(n=>n.id)); selectedRef.current=ns; setSelected(ns)
          }
        }
      }
      if(isPanning.current){
        const np={x:e.clientX-panStart.current.x,y:e.clientY-panStart.current.y}
        panRef.current=np
        setPan(np)
        return
      }
      const d=draggingRef.current
      if(d){
        const nx=c.x-dragOffsetRef.current.x
        const ny=c.y-dragOffsetRef.current.y
        if(d.kind==='node'){
          nodesRef.current=nodesRef.current.map(n=>n.id===d.id?{...n,x:nx,y:ny}:n)
          setNodes([...nodesRef.current])
        }
        if(d.kind==='net'){
          networksRef.current=networksRef.current.map(n=>n.id===d.id?{...n,x:nx,y:ny}:n)
          setNetworks([...networksRef.current])
        }
        if(d.kind==='text'){
          setTexts(p=>p.map(t=>t.id===d.id?{...t,x:nx,y:ny}:t))
        }
      }
    }
    const onUp=(e)=>{
      // CRE-64: Finish drawing shape
      if(drawingShape){
        const {type,startX,startY,endX,endY} = drawingShape
        const width = Math.abs(endX - startX)
        const height = Math.abs(endY - startY)
        
        // Only create shape if it's bigger than 10px (avoid accidental clicks)
        if(width > 10 || height > 10){
          const shapeId = 'shape-' + Date.now()
          const newShape = {
            id:shapeId,
            type,
            x:Math.min(startX,endX),
            y:Math.min(startY,endY),
            width,
            height,
            fill:drawFillColor,
            stroke:drawStrokeColor,
            text:'' // empty text for shapes
          }
          setTexts(p=>[...p,newShape])
          // CRE-64: Persist to database
          createTextObject(labId, {
            type, x: newShape.x, y: newShape.y,
            width, height,
            fill: drawFillColor, stroke: drawStrokeColor,
            text: '', z_index: 0
          }).catch(err=>console.error('Failed to save shape:', err))
        }
        setDrawingShape(null)
        return
      }
      
      selBoxStart.current=null
      setSelBox(null)
      isPanning.current=false
      if(draggingRef.current){
        // CRE-64: Persist text object position after drag
        if(draggingRef.current.kind === 'text'){
          const draggedObj = texts.find(t => t.id === draggingRef.current.id)
          if(draggedObj){
            updateTextObject(labId, draggedObj.id, {
              x: draggedObj.x,
              y: draggedObj.y
            }).catch(err=>console.error('Failed to update position:', err))
          }
        }
        draggingRef.current=null
        return
      }
      if(connectingRef.current){
        const c=toCanvas(e.clientX,e.clientY)
        const tn=hitNode(c.x,c.y)
        const tnet=hitNet(c.x,c.y)
        if(tn&&tn.id!==connectingRef.current.srcId){
          setIfaceModal({srcId:connectingRef.current.srcId,dstId:tn.id,dstKind:'node'})
        } else if(tnet){
          setIfaceModal({srcId:connectingRef.current.srcId,dstId:tnet.id,dstKind:'net'})
        }
        connectingRef.current=null
        setConnecting(null)
      }
    }
    window.addEventListener('mousemove',onMove)
    window.addEventListener('mouseup',onUp)
    return()=>{ window.removeEventListener('mousemove',onMove); window.removeEventListener('mouseup',onUp) }
  },[])

  const startDrag=(e,kind,id,objX,objY)=>{
    e.stopPropagation()
    const c=toCanvas(e.clientX,e.clientY)
    draggingRef.current={kind,id}
    dragOffsetRef.current={x:c.x-objX,y:c.y-objY}
    setSelected(id)
    setContextMenu(null)
  }

  const startConnect=(e,nodeId)=>{
    e.stopPropagation()
    e.preventDefault()
    connectingRef.current={srcId:nodeId}
    setConnecting({srcId:nodeId})
  }

  const finishLink=(si,di)=>{
    if(!ifaceModal)return
    setLinks(p=>[...p,{
      id:'lnk-'+Date.now(),
      srcId:ifaceModal.srcId,
      dstId:ifaceModal.dstKind==='node'?ifaceModal.dstId:null,
      netId:ifaceModal.dstKind==='net'?ifaceModal.dstId:null,
      srcIface:si,dstIface:di,style:'solid'
    }])
    setIfaceModal(null)
  }

  const onSvgMouseDown=(e)=>{
    if(e.button===1||(e.button===0&&e.altKey)){
      isPanning.current=true
      panStart.current={x:e.clientX-panRef.current.x,y:e.clientY-panRef.current.y}
      e.preventDefault(); return
    }
    
    // CRE-64: Drawing mode active
    if(drawingTool !== 'select' && (e.target===svgRef.current||e.target.dataset?.canvas)){
      const r=svgRef.current.getBoundingClientRect()
      const cx=(e.clientX-r.left-panRef.current.x)/zoomRef.current
      const cy=(e.clientY-r.top-panRef.current.y)/zoomRef.current
      
      if(drawingTool === 'text'){
        const text = prompt('Enter text:')
        if(text){
          const textId = 'txt-'+Date.now()
          setTexts(p=>[...p,{id:textId,text,x:cx,y:cy,type:'text'}])
          // CRE-64: Persist text annotation to database
          createTextObject(labId, {
            type: 'text', x: cx, y: cy,
            text, fill: drawFillColor, stroke: drawStrokeColor,
            z_index: 0
          }).catch(err=>console.error('Failed to save text:', err))
        }
        return
      }
      
      // Start drawing shape (rectangle or circle)
      setDrawingShape({type:drawingTool,startX:cx,startY:cy,endX:cx,endY:cy})
      return
    }
    
    if(e.target===svgRef.current||e.target.dataset?.canvas){
      setContextMenu(null)
      const ns=new Set(); selectedRef.current=ns; setSelected(ns)
      // Start drag-select box
      const r=svgRef.current.getBoundingClientRect()
      const cx=(e.clientX-r.left-panRef.current.x)/zoomRef.current
      const cy=(e.clientY-r.top-panRef.current.y)/zoomRef.current
      selBoxStart.current={x:cx,y:cy}
      setSelBox({x:cx,y:cy,w:0,h:0})
    }
  }

  const onWheel=(e)=>{
    e.preventDefault()
    const d=e.deltaY>0?0.9:1.1
    const nz=Math.min(4,Math.max(0.15,zoomRef.current*d))
    zoomRef.current=nz
    setZoom(nz)
  }

  const onRightClick=(e)=>{
    e.preventDefault()
    const c=toCanvas(e.clientX,e.clientY)
    setContextMenu({x:e.clientX,y:e.clientY,kind:'canvas',coords:c})
  }
  const onNodeRightClick=(e,node)=>{
    e.preventDefault();e.stopPropagation()
    // If right-clicking a node NOT in current selection, select only that node
    // If right-clicking a node IN selection, keep the whole selection
    if(!selectedRef.current.has(node.id)){
      const ns=new Set([node.id]); selectedRef.current=ns; setSelected(ns)
    }
    setContextMenu({x:e.clientX,y:e.clientY,kind:'node',node})
  }
  const onNetRightClick=(e,net)=>{
    e.preventDefault();e.stopPropagation()
    setContextMenu({x:e.clientX,y:e.clientY,kind:'net',net})
  }
  const onLinkRightClick=(e,link)=>{
    e.preventDefault();e.stopPropagation()
    setContextMenu({x:e.clientX,y:e.clientY,kind:'link',link})
  }

  const addNodeToCanvas=(vendorType,coords)=>{
    const def=VENDORS[vendorType]
    setNodePrefix((def?.label||'Node')+'-')
    setQty(1); setStartNum(1)
    setPendingAdd({vendorType,coords})
    setAddNodeModal(null)
  }

  const confirmAddNodes=async()=>{
    if(!pendingAdd)return
    const {vendorType,coords}=pendingAdd
    const def=VENDORS[vendorType]
    const nodeType=['router','switch_l2','switch_l3'].includes(def?.shape)?'qemu':'docker'
    const cols=Math.min(qty,4)
    const newNodes=[]
    for(let i=0;i<qty;i++){
      const nm=qty===1?nodePrefix.replace(/-+$/,''):nodePrefix+(startNum+i)
      const x=Math.round(coords.x+(i%cols)*200)
      const y=Math.round(coords.y+Math.floor(i/cols)*160)
      try{
        const r=await addNode({lab_id:labId,name:nm,type:nodeType,image:null,x,y})
        newNodes.push({id:r.data.id,name:nm,vendorType,x,y,status:'stopped'})
      }catch{
        newNodes.push({id:'tmp-'+Date.now()+i,name:nm,vendorType,x,y,status:'stopped'})
      }
    }
    setNodes(p=>[...p,...newNodes])
    setPendingAdd(null); setQty(1); setNodePrefix('')
  }



  // ── Interface usage tracking ──────────────────────────────
  const usedIfaces = (nodeId) => {
    const used = { src: new Set(), dst: new Set() }
    links.forEach(l => {
      if (l.srcId === nodeId) used.src.add(l.srcIface)
      if (l.dstId === nodeId) used.dst.add(l.dstIface)
    })
    return new Set([...used.src, ...used.dst])
  }

  const availableIfaces = (nodeId) => {
    const def = VENDORS[nodes.find(n => n.id === nodeId)?.vendorType]
    const allIfaces = def?.ifaces || IFACES
    const used = usedIfaces(nodeId)
    return { all: allIfaces, used }
  }


  const nextAvailableIface = (nodeId) => {
    const { all, used } = availableIfaces(nodeId)
    return all.find(i => !used.has(i)) || all[0]
  }

  const menuItems=(kind,item)=>{
    if(kind==='canvas')return[
      {l:'⊕  Add Node',a:()=>{setAddNodeModal(item.coords);setContextMenu(null)}},
      {l:'⊞  Add Network',a:()=>{setAddNetModal(item.coords);setContextMenu(null)}},
      {l:'T  Add Text Label',a:()=>{const t=prompt('Label:');if(t)setTexts(p=>[...p,{id:'txt-'+Date.now(),text:t,...item.coords}]);setContextMenu(null)}},
    ]
    if(kind==='node')return[
      {l:item.node?.status==='running'?'⬛  Stop Node':'▶  Start Node',a:()=>{setNodes(p=>p.map(n=>n.id===item.node.id?{...n,status:n.status==='running'?'stopped':'running'}:n));setContextMenu(null)}},
      {l:'🖥  Open Console',a:()=>{alert('Console: '+item.node?.name);setContextMenu(null)}},
      {l:'🔗  Add Link from here',a:()=>{connectingRef.current={srcId:item.node.id};setConnecting({srcId:item.node.id});setContextMenu(null)}},
      {l:'✎  Rename',a:()=>{const v=prompt('Name:',item.node?.name);if(v)setNodes(p=>p.map(n=>n.id===item.node.id?{...n,name:v}:n));setContextMenu(null)}},
      {l:'⚙  Configure...',a:()=>{setSelectedNode({id:item.node.id,data:{label:item.node?.name,type:item.node?.type,config:item.node?.config}});setContextMenu(null)}},
      {l:'⟳  Wipe Node',a:()=>setContextMenu(null)},
      {l: selectedRef.current.size>1 ? '🗑'+'  Delete All Selected ('+selectedRef.current.size+')' : '🗑'+'  Delete Node',col:'#dc2626',a:()=>{
        const toDelete = selectedRef.current.size > 1 ? new Set(selectedRef.current) : new Set([item.node.id])
        const pos={x:contextMenu?.x||600,y:contextMenu?.y||300}
        setConfirmDel({toDelete:new Set(toDelete),pos})
        setContextMenu(null)
        setContextMenu(null)
      }},
    ]
    if(kind==='net')return[
      {l:'✎  Rename',a:()=>{const v=prompt('Name:',item.net?.name);if(v)setNetworks(p=>p.map(n=>n.id===item.net.id?{...n,name:v}:n));setContextMenu(null)}},
      {l:'🗑  Delete',col:'#dc2626',a:()=>{setNetworks(p=>p.filter(n=>n.id!==item.net.id));setContextMenu(null)}},
    ]
    if(kind==='link')return[
      {l:'— Solid',a:()=>{setLinks(p=>p.map(l=>l.id===item.link.id?{...l,style:'solid'}:l));setContextMenu(null)}},
      {l:'- - Dashed',a:()=>{setLinks(p=>p.map(l=>l.id===item.link.id?{...l,style:'dashed'}:l));setContextMenu(null)}},
      {l:'··· Dotted',a:()=>{setLinks(p=>p.map(l=>l.id===item.link.id?{...l,style:'dotted'}:l));setContextMenu(null)}},
      {l:'🗑  Delete Link',col:'#dc2626',a:()=>{setLinks(p=>p.filter(l=>l.id!==item.link.id));setContextMenu(null)}},
    ]
    if(kind==='text')return[
      {l:'✎  Edit Text',a:()=>{
        const v=prompt('Edit text:',item.text?.text||'')
        if(v!==null){
          setTexts(p=>p.map(t=>t.id===item.text.id?{...t,text:v}:t))
          updateTextObject(labId, item.text.id, {text:v}).catch(err=>console.error('Failed to update text:', err))
        }
        setContextMenu(null)
      }},
      {l:'🗑  Delete',col:'#dc2626',a:()=>{
        setTexts(p=>p.filter(t=>t.id!==item.text.id))
        deleteTextObject(labId, item.text.id).catch(err=>console.error('Failed to delete:', err))
        setContextMenu(null)
      }},
    ]
    return[]
  }

  if(loading)return<div style={{display:'flex',alignItems:'center',justifyContent:'center',height:'100%',background:'#fff',color:'#999',fontFamily:'sans-serif'}}>Loading lab...</div>

  const runCount=nodes.filter(n=>n.status==='running').length
  const srcNode=connecting?nodes.find(n=>n.id===connecting.srcId):null

  return(
    <div style={{display:'flex',height:'100%',flexDirection:'column',fontFamily:'sans-serif',background:bg,userSelect:'none'}} onClick={()=>setContextMenu(null)}>

      <div style={{height:38,background:darkMode?'#1e293b':'#f8fafc',borderBottom:'1px solid '+bc,display:'flex',alignItems:'center',padding:'0 14px',gap:10,flexShrink:0}}>
        <span style={{fontSize:13,fontWeight:600,color:tc,marginRight:4}}>{labName}</span>
        <div style={{width:1,height:20,background:bc}}/>
        <button onClick={()=>setNodes(p=>p.map(n=>({...n,status:'running'})))}
          style={{fontSize:12,padding:'3px 12px',border:'1px solid '+(runCount===nodes.length&&nodes.length>0?'#9ca3af':'#16a34a'),borderRadius:4,background:runCount===nodes.length&&nodes.length>0?'transparent':'#f0fdf4',color:runCount===nodes.length&&nodes.length>0?'#9ca3af':'#16a34a',cursor:runCount===nodes.length&&nodes.length>0?'default':'pointer',display:'flex',alignItems:'center',gap:4}}
          disabled={runCount===nodes.length&&nodes.length>0}>
          <svg width="10" height="10"><polygon points="1,1 9,5 1,9" fill={runCount===nodes.length&&nodes.length>0?'#9ca3af':'#16a34a'}/></svg>Start All
        </button>
        <button onClick={()=>setNodes(p=>p.map(n=>({...n,status:'stopped'})))}
          style={{fontSize:12,padding:'3px 12px',border:'1px solid '+(runCount===0||nodes.length===0?'#9ca3af':'#dc2626'),borderRadius:4,background:runCount===0||nodes.length===0?'transparent':'#fef2f2',color:runCount===0||nodes.length===0?'#9ca3af':'#dc2626',cursor:runCount===0||nodes.length===0?'default':'pointer',display:'flex',alignItems:'center',gap:4}}
          disabled={runCount===0||nodes.length===0}>
          <svg width="10" height="10"><rect x="1" y="1" width="8" height="8" fill={runCount===0||nodes.length===0?'#9ca3af':'#dc2626'}/></svg>Stop All
        </button>
        <div style={{flex:1}}/>
        <span style={{fontSize:11,color:sc,background:darkMode?'#0f172a':'#f1f5f9',padding:'2px 8px',borderRadius:4,border:'1px solid '+bc}}>{runCount}/{nodes.length} running</span>
        <button onClick={()=>setDarkMode(d=>!d)} style={{fontSize:11,padding:'3px 10px',border:'1px solid '+bc,borderRadius:4,background:'transparent',color:sc,cursor:'pointer'}}>{darkMode?'☀':'🌙'}</button>
        <button onClick={()=>setHideLabels(h=>!h)} style={{fontSize:11,padding:'3px 10px',border:'1px solid '+bc,borderRadius:4,background:'transparent',color:sc,cursor:'pointer'}}>{hideLabels?'Show Labels':'Hide Labels'}</button>
        <button onClick={()=>navigate('/')} style={{fontSize:11,padding:'3px 10px',border:'1px solid '+bc,borderRadius:4,background:'transparent',color:sc,cursor:'pointer'}}>✕ Close</button>
      </div>

      <div style={{display:'flex',flex:1,overflow:'hidden'}}>
        <div style={{width:40,background:darkMode?'#0f172a':'#f1f5f9',borderRight:'1px solid '+bc,display:'flex',flexDirection:'column',alignItems:'center',paddingTop:8,gap:4,flexShrink:0}}>
          {[
            {ic:'⊕',tip:'Add Node',fn:()=>setAddNodeModal({x:300,y:200})},
            {ic:'⊞',tip:'Add Network',fn:()=>setAddNetModal({x:300,y:200})},
            {ic:'T',tip:'Add Text',fn:()=>{const t=prompt('Text:');if(t)setTexts(p=>[...p,{id:'txt-'+Date.now(),text:t,x:200,y:200}])}},
            {ic:'📊',tip:'Traffic Filters',fn:()=>setShowTrafficFilters(s=>!s)}, // CRE-68
            {ic:'↺',tip:'Refresh',fn:()=>window.location.reload()},
            {ic:'⤢',tip:'Reset View',fn:()=>{panRef.current={x:80,y:40};setPan({x:80,y:40});zoomRef.current=1;setZoom(1)}},
            {ic:'▦',tip:'Minimap',fn:()=>setShowMinimap(m=>!m)},
          ].map((b,i)=>(
            <div key={i} onClick={b.fn} title={b.tip}
              style={{width:32,height:32,display:'flex',alignItems:'center',justifyContent:'center',borderRadius:4,cursor:'pointer',fontSize:b.ic==='T'?14:18,color:sc}}
              onMouseEnter={e=>e.currentTarget.style.background=darkMode?'#1e293b':'#e5e7eb'}
              onMouseLeave={e=>e.currentTarget.style.background='transparent'}>{b.ic}</div>
          ))}
        </div>

        <div style={{flex:1,position:'relative',overflow:'hidden'}}>
          <svg ref={svgRef} width="100%" height="100%"
            style={{display:'block',cursor:connecting?'crosshair':draggingRef.current?'grabbing':'default'}}
            onMouseDown={onSvgMouseDown}
            onContextMenu={onRightClick}
            onWheel={onWheel}>
            <defs>
              <pattern id="sg" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M20 0L0 0 0 20" fill="none" stroke={gridSm} strokeWidth="0.5"/>
              </pattern>
              <pattern id="lg" width="100" height="100" patternUnits="userSpaceOnUse">
                <rect width="100" height="100" fill="url(#sg)"/>
                <path d="M100 0L0 0 0 100" fill="none" stroke={gridLg} strokeWidth="0.5"/>
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#lg)" data-canvas="1"/>

            <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}>

              {links.map(link=>{
                const src=nodes.find(n=>n.id===link.srcId)
                const dst=link.dstId?nodes.find(n=>n.id===link.dstId):null
                const net=link.netId?networks.find(n=>n.id===link.netId):null
                const dstObj=dst||net
                if(!src||!dstObj)return null
                const sx=src.x+24,sy=src.y+24
                const dx=dstObj.x+(net?30:24),dy=dstObj.y+(net?25:24)
                
                // CRE-66: Link styling
                const linkColor = link.color || (darkMode?'#475569':'#9ca3af')
                const linkWidth = link.width || 1.5
                const dash = link.style==='Dashed'?'8,4':undefined
                
                // Path generation based on linkstyle
                let pathD = `M${sx},${sy} L${dx},${dy}` // Default: Straight
                if(link.linkstyle==='Bezier'){
                  const midX=(sx+dx)/2, midY=(sy+dy)/2
                  const perpX=-(dy-sy)/4, perpY=(dx-sx)/4
                  const cp1x=midX+perpX, cp1y=midY+perpY
                  pathD=`M${sx},${sy} Q${cp1x},${cp1y} ${dx},${dy}`
                }else if(link.linkstyle==='Flowchart'){
                  const midX=(sx+dx)/2
                  pathD=`M${sx},${sy} L${midX},${sy} L${midX},${dy} L${dx},${dy}`
                }
                
                const angle=Math.atan2(dy-sy,dx-sx)*180/Math.PI
                const d=58
                const sxe=sx+Math.cos(angle*Math.PI/180)*d, sye=sy+Math.sin(angle*Math.PI/180)*d
                const dxe=dx-Math.cos(angle*Math.PI/180)*d, dye=dy-Math.sin(angle*Math.PI/180)*d
                const rot=angle>90||angle<-90?angle+180:angle
                
                // Label midpoint calculation
                const labelX=sx+(dx-sx)*link.labelpos
                const labelY=sy+(dy-sy)*link.labelpos
                
                return(
                  <g key={link.id} style={{cursor:'context-menu'}} onContextMenu={e=>onLinkRightClick(e,link)}>
                    <path d={pathD} stroke={linkColor} strokeWidth={linkWidth} strokeDasharray={dash} fill="none"/>
                    <path d={pathD} stroke="transparent" strokeWidth="14" fill="none"/>
                    {!hideLabels&&<>
                      {/* CRE-65-B: Source interface label (always shown) */}
                      <text x={sxe} y={sye} textAnchor="middle" fontSize="8" fill={darkMode?'#60a5fa':'#2563eb'} fontFamily="monospace"
                        transform={`rotate(${rot},${sxe},${sye})`}>
                        {link.srcIface.replace('GigabitEthernet','Gi').replace('FastEthernet','Fa')}
                      </text>
                      
                      {/* CRE-65-B: Destination interface label (node-to-node OR node-to-network) */}
                      {dst ? (
                        // Node-to-node: show destination node interface
                        <text x={dxe} y={dye} textAnchor="middle" fontSize="8" fill={darkMode?'#60a5fa':'#2563eb'} fontFamily="monospace"
                          transform={`rotate(${rot},${dxe},${dye})`}>
                          {link.dstIface.replace('GigabitEthernet','Gi').replace('FastEthernet','Fa')}
                        </text>
                      ) : (
                        // Node-to-network: show network name at connection point
                        <text x={dxe} y={dye} textAnchor="middle" fontSize="9" fill={darkMode?'#a78bfa':'#7c3aed'} fontFamily="sans-serif" fontWeight="600"
                          transform={`rotate(${rot},${dxe},${dye})`}>
                          {net.name}
                        </text>
                      )}
                      
                      {/* Link label (custom text) */}
                      {link.label&&(
                        <text x={labelX} y={labelY-8} textAnchor="middle" fontSize="10" fill={linkColor} fontWeight="600" fontFamily="sans-serif"
                          transform={`rotate(${rot},${labelX},${labelY-8})`}>
                          {link.label}
                        </text>
                      )}
                    </>}
                  </g>
                )
              })}

              {/* CRE-68 Phase 3: Animated traffic particles */}
              <LinkAnimationEngine 
                links={links.map(link => {
                  const src = nodes.find(n => n.id === link.srcId)
                  const dst = link.dstId ? nodes.find(n => n.id === link.dstId) : null
                  const net = link.netId ? networks.find(n => n.id === link.netId) : null
                  const dstObj = dst || net
                  if (!src || !dstObj) return null
                  
                  const sx = src.x + 24, sy = src.y + 24
                  const dx = dstObj.x + (net ? 30 : 24), dy = dstObj.y + (net ? 25 : 24)
                  
                  // Generate path (same logic as link rendering above)
                  let pathD = `M${sx},${sy} L${dx},${dy}`
                  if (link.linkstyle === 'Bezier') {
                    const midX = (sx + dx) / 2, midY = (sy + dy) / 2
                    const perpX = -(dy - sy) / 4, perpY = (dx - sx) / 4
                    const cp1x = midX + perpX, cp1y = midY + perpY
                    pathD = `M${sx},${sy} Q${cp1x},${cp1y} ${dx},${dy}`
                  } else if (link.linkstyle === 'Flowchart') {
                    const midX = (sx + dx) / 2
                    pathD = `M${sx},${sy} L${midX},${sy} L${midX},${dy} L${dx},${dy}`
                  }
                  
                  return { id: link.id, path: pathD }
                }).filter(Boolean)}
                trafficEvents={trafficEvents}
                activeFilters={wsActiveFilters}
              />

              {selBox && selBox.w > 5 && selBox.h > 5 && (
                <rect x={selBox.x} y={selBox.y} width={selBox.w} height={selBox.h}
                  fill="#3b82f622" stroke="#3b82f6" strokeWidth="1.5" strokeDasharray="5,3"
                  pointerEvents="none"/>
              )}

              {connecting&&srcNode&&(
                <line x1={srcNode.x+24} y1={srcNode.y+24} x2={mousePos.x} y2={mousePos.y}
                  stroke="#3b82f6" strokeWidth="2" strokeDasharray="8,4" pointerEvents="none"/>
              )}

              {networks.map(net=>{
                const def=NET_DEFS[net.type]||NET_DEFS.bridge; const c=def.color
                // CRE-65-A: Count connections to this network
                const connectionCount = links.filter(l=>l.netId===net.id).length
                // CRE-65-C: Size scaling based on connections (min 60, max 100)
                const baseSize = 60
                const sizeBonus = Math.min(40, connectionCount * 8)
                const totalSize = baseSize + sizeBonus
                const scale = totalSize / 60
                const isSelected = selected instanceof Set ? selected.has(net.id) : false
                const isHovered = hoveredId === net.id
                
                return(
                  <g key={net.id} transform={`translate(${net.x},${net.y})`} style={{cursor:'grab'}}
                    onMouseEnter={()=>setHoveredId(net.id)}
                    onMouseLeave={()=>setHoveredId(null)}
                    onContextMenu={e=>onNetRightClick(e,net)}>
                    <rect x="-4" y="-4" width="68" height="72" fill="transparent"
                      onMouseDown={e=>startDrag(e,'net',net.id,net.x,net.y)}/>
                    
                    {/* CRE-65-C: Selection and hover states */}
                    {isSelected&&<rect x="-6" y="-2" width="72" height="70" rx="6" fill="none" stroke="#a78bfa" strokeWidth="2" strokeDasharray="5,3" style={{pointerEvents:'none'}}/>}
                    {isHovered&&!isSelected&&<rect x="-4" y="0" width="68" height="66" rx="5" fill={darkMode?'#ffffff08':'#f5f3ff'} stroke={darkMode?'#334155':'#ddd6fe'} strokeWidth="1" style={{pointerEvents:'none'}}/>}
                    
                    <g transform={`scale(${scale})`} transform-origin="30 24">
                      {/* CRE-65-A: Enhanced network icons with better visual distinction */}
                      {net.type==='nat'?
                        // Cloud icon for NAT/Internet
                        <g>
                          <path d="M8 36 Q4 36 4 28 Q4 20 12 20 Q12 12 20 12 Q25 10 30 14 Q36 10 40 14 Q48 14 48 22 Q48 30 44 32 Q46 36 42 36 Z" 
                            fill={`${c}44`} stroke={c} strokeWidth="2.5"/>
                          <text x="25" y="30" textAnchor="middle" fontSize="16" fill={c} fontFamily="sans-serif" style={{pointerEvents:'none'}}>☁</text>
                        </g>
                      :net.type==='internal'?
                        // Line topology for internal network
                        <g>
                          <line x1="4" y1="24" x2="56" y2="24" stroke={c} strokeWidth="5"/>
                          {[12,24,36,48].map(x=><circle key={x} cx={x} cy="24" r="6" fill={c} stroke={bg} strokeWidth="1"/>)}
                        </g>
                      :
                        // Bridge/Switch icon (default)
                        <g>
                          <rect x="4" y="10" width="52" height="20" rx="3" fill={`${c}44`} stroke={c} strokeWidth="2.5"/>
                          {[14,24,34,44].map(x=><line key={x} x1={x} y1="10" x2={x} y2="30" stroke={c} strokeWidth="1.5"/>)}
                        </g>
                      }
                    </g>
                    
                    {/* CRE-65-A: Always-visible network label */}
                    <text x="34" y="56" textAnchor="middle" fontSize="11" fill={tc} fontWeight="600" fontFamily="sans-serif" style={{pointerEvents:'none'}}>
                      {net.name}
                    </text>
                    
                    {/* CRE-65-C: Status indicator (active if has connections) */}
                    <circle cx="34" cy="62" r="3" fill={connectionCount>0?'#22c55e':'#9ca3af'} style={{pointerEvents:'none'}}/>
                    
                    {/* CRE-65-A: Connection count badge */}
                    {connectionCount > 0 && (
                      <g>
                        <circle cx="56" cy="8" r="9" fill={c} stroke={bg} strokeWidth="2.5"/>
                        <text x="56" y="12" textAnchor="middle" fontSize="11" fill={bg} fontWeight="700" fontFamily="sans-serif" style={{pointerEvents:'none'}}>
                          {connectionCount}
                        </text>
                      </g>
                    )}
                    
                    {/* Connect port (top center) */}
                    <circle cx="34" cy="5" r="6" fill={c} stroke={bg} strokeWidth="2" style={{cursor:'crosshair'}} onMouseDown={e=>startConnect(e,net.id)}/>
                  </g>
                )
              })}

              {nodes.map(node=>{
                const def=VENDORS[node.vendorType]||VENDORS['generic-router']
                const running=node.status==='running'
                const c=running?def.color:'#9ca3af'
                const isSelected=selected instanceof Set ? selected.has(node.id) : false
                const isHovered=hoveredId===node.id
                const showPorts=isHovered||isSelected||!!connecting
                return(
                  <g key={node.id} transform={`translate(${node.x},${node.y})`}
                    onMouseEnter={()=>setHoveredId(node.id)}
                    onMouseLeave={()=>setHoveredId(null)}
                    onContextMenu={e=>onNodeRightClick(e,node)}
                    onDoubleClick={()=>alert('Console: '+node.name)}>

                    {/* ★ Full transparent hit area — the ONE place that handles drag ★ */}
                    <rect x="-8" y="-8" width="64" height="88" fill="transparent" rx="4"
                      onContextMenu={e=>onNodeRightClick(e,node)}
                      style={{cursor:connecting?'crosshair':'grab'}}
                      onMouseDown={e=>{ if(!connecting) startDrag(e,'node',node.id,node.x,node.y) }}/>

                    {isSelected&&<rect x="-6" y="-6" width="60" height="84" rx="6" fill="none" stroke="#3b82f6" strokeWidth="1.5" strokeDasharray="5,3" style={{pointerEvents:'none'}}/>}
                    {isHovered&&!isSelected&&<rect x="-4" y="-4" width="56" height="80" rx="5" fill={darkMode?'#ffffff08':'#f0f9ff'} stroke={darkMode?'#334155':'#bfdbfe'} strokeWidth="1" style={{pointerEvents:'none'}}/>}

                    <g style={{pointerEvents:'none'}}>
                      <NodeIcon type={node.vendorType} color={c} size={48} muted={!running}/>
                    </g>

                    {!hideLabels&&<>
                      <text x="24" y="60" textAnchor="middle" fontSize="11" fill={tc} fontWeight="500" fontFamily="sans-serif" style={{pointerEvents:'none'}}>{node.name}</text>
                      <circle cx="24" cy="68" r="3" fill={running?'#22c55e':'#9ca3af'} style={{pointerEvents:'none'}}/>
                    </>}

                    {showPorts&&<>
                      <circle cx="52" cy="24" r="6" fill={c} stroke={bg} strokeWidth="2" style={{cursor:'crosshair'}} onMouseDown={e=>startConnect(e,node.id)} title="Gi0/0"/>
                      <circle cx="24" cy="-6" r="6" fill={c} stroke={bg} strokeWidth="2" style={{cursor:'crosshair'}} onMouseDown={e=>startConnect(e,node.id)} title="Gi0/1"/>
                      <circle cx="-6" cy="24" r="6" fill={c} stroke={bg} strokeWidth="2" style={{cursor:'crosshair'}} onMouseDown={e=>startConnect(e,node.id)} title="Gi0/2"/>
                      <circle cx="24" cy="54" r="6" fill={c} stroke={bg} strokeWidth="2" style={{cursor:'crosshair'}} onMouseDown={e=>startConnect(e,node.id)} title="eth0"/>
                    </>}
                  </g>
                )
              })}

              {texts.map(t=>{
                // CRE-64: Render shapes (rectangles/circles) or text
                if(t.type === 'rectangle'){
                  return (
                    <rect key={t.id} x={t.x} y={t.y} width={t.width} height={t.height}
                      fill={t.fill} stroke={t.stroke} strokeWidth={2}
                      onMouseDown={e=>startDrag(e,'text',t.id,t.x,t.y)}
                      onContextMenu={e=>{e.preventDefault();e.stopPropagation();setContextMenu({x:e.clientX,y:e.clientY,kind:'text',text:t})}}
                      style={{cursor:'move'}}/>
                  )
                } else if(t.type === 'circle'){
                  return (
                    <ellipse key={t.id}
                      cx={t.x + t.width/2} cy={t.y + t.height/2}
                      rx={t.width/2} ry={t.height/2}
                      fill={t.fill} stroke={t.stroke} strokeWidth={2}
                      onMouseDown={e=>startDrag(e,'text',t.id,t.x,t.y)}
                      onContextMenu={e=>{e.preventDefault();e.stopPropagation();setContextMenu({x:e.clientX,y:e.clientY,kind:'text',text:t})}}
                      style={{cursor:'move'}}/>
                  )
                } else {
                  // Regular text
                  return (
                    <text key={t.id} x={t.x} y={t.y} fontSize={t.size||14} fill={tc} fontFamily="sans-serif"
                      onMouseDown={e=>startDrag(e,'text',t.id,t.x,t.y)}
                      onContextMenu={e=>{e.preventDefault();e.stopPropagation();setContextMenu({x:e.clientX,y:e.clientY,kind:'text',text:t})}}
                      onDoubleClick={()=>{const v=prompt('Edit:',t.text);if(v!==null){setTexts(p=>p.map(tx=>tx.id===t.id?{...tx,text:v}:tx));updateTextObject(labId,t.id,{text:v}).catch(err=>console.error('Update failed:',err))}}} style={{cursor:'move'}}>{t.text}</text>
                  )
                }
              })}
              
              {/* CRE-64: Preview shape being drawn */}
              {drawingShape && drawingShape.type === 'rectangle' && (
                <rect
                  x={Math.min(drawingShape.startX,drawingShape.endX)}
                  y={Math.min(drawingShape.startY,drawingShape.endY)}
                  width={Math.abs(drawingShape.endX-drawingShape.startX)}
                  height={Math.abs(drawingShape.endY-drawingShape.startY)}
                  fill={drawFillColor}
                  stroke={drawStrokeColor}
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  pointerEvents="none"/>
              )}
              {drawingShape && drawingShape.type === 'circle' && (
                <ellipse
                  cx={(drawingShape.startX+drawingShape.endX)/2}
                  cy={(drawingShape.startY+drawingShape.endY)/2}
                  rx={Math.abs(drawingShape.endX-drawingShape.startX)/2}
                  ry={Math.abs(drawingShape.endY-drawingShape.startY)/2}
                  fill={drawFillColor}
                  stroke={drawStrokeColor}
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  pointerEvents="none"/>
              )}
            </g>
          </svg>

          {contextMenu&&(
            <div onClick={e=>e.stopPropagation()} style={{position:'fixed',left:contextMenu.x,top:contextMenu.y,background:cb,border:'1px solid '+cbb,borderRadius:8,boxShadow:'0 4px 24px rgba(0,0,0,0.15)',zIndex:999,minWidth:200,overflow:'hidden',fontFamily:'sans-serif'}}>
              {menuItems(contextMenu.kind,contextMenu).map(item=>(
                <div key={item.l} onClick={item.a} style={{padding:'9px 16px',fontSize:13,color:item.col||tc,cursor:'pointer',borderBottom:'1px solid '+bc}}
                  onMouseEnter={e=>e.currentTarget.style.background=darkMode?'#334155':'#f8fafc'}
                  onMouseLeave={e=>e.currentTarget.style.background='transparent'}>{item.l}</div>
              ))}
            </div>
          )}

          {connecting&&<>
            <div style={{position:'absolute',bottom:48,left:'50%',transform:'translateX(-50%)',background:'#1d4ed8',color:'white',padding:'6px 20px',borderRadius:20,fontSize:12,fontWeight:500,pointerEvents:'none',zIndex:10}}>
              Click destination node or network to connect
            </div>
            <button onClick={()=>{connectingRef.current=null;setConnecting(null)}} style={{position:'absolute',top:8,right:8,fontSize:12,padding:'4px 14px',background:'#fee2e2',border:'1px solid #fca5a5',borderRadius:4,color:'#dc2626',cursor:'pointer',zIndex:10}}>ESC Cancel</button>
          </>}

          {showMinimap&&nodes.length>0&&(
            <div style={{position:'absolute',bottom:12,right:12,width:180,height:120,background:darkMode?'rgba(15,23,42,0.95)':'rgba(255,255,255,0.97)',border:'1px solid '+bc,borderRadius:8,overflow:'hidden',boxShadow:'0 2px 8px rgba(0,0,0,0.1)'}}>
              <div style={{fontSize:9,color:sc,padding:'3px 6px',borderBottom:'1px solid '+bc}}>Minimap</div>
              <svg width="180" height="100">
                {links.map(l=>{const s2=nodes.find(n=>n.id===l.srcId),d2=nodes.find(n=>n.id===l.dstId);if(!s2||!d2)return null;return<line key={l.id} x1={s2.x/8+10} y1={s2.y/8+5} x2={d2.x/8+10} y2={d2.y/8+5} stroke={darkMode?'#475569':'#d1d5db'} strokeWidth="1"/>})}
                {nodes.map(n=>{const d2=VENDORS[n.vendorType]||VENDORS['generic-router'];return<circle key={n.id} cx={n.x/8+10} cy={n.y/8+5} r="5" fill={n.status==='running'?d2.color:'#9ca3af'}/>})}
              </svg>
            </div>
          )}
          
          {/* CRE-64: Drawing Toolbar */}
          <DrawingToolbar
            activeTool={drawingTool}
            onToolChange={setDrawingTool}
            fillColor={drawFillColor}
            strokeColor={drawStrokeColor}
            onFillChange={setDrawFillColor}
            onStrokeChange={setDrawStrokeColor}
          />

          <div style={{position:'absolute',bottom:12,left:48,fontSize:10,color:sc,background:darkMode?'rgba(15,23,42,0.85)':'rgba(255,255,255,0.92)',padding:'3px 10px',borderRadius:4,border:'1px solid '+bc,pointerEvents:'none'}}>
            Right-click to add · Drag canvas to multi-select · Ctrl+click to add to selection · Delete key removes selection · Alt+drag to pan
          </div>
        </div>
      </div>

      {addNodeModal&&(
        <div style={{position:'fixed',inset:0,background:'rgba(0,0,0,0.45)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:2000}} onClick={()=>setAddNodeModal(null)}>
          <div onClick={e=>e.stopPropagation()} style={{background:cb,borderRadius:12,padding:0,width:640,maxHeight:'85vh',display:'flex',flexDirection:'column',boxShadow:'0 20px 60px rgba(0,0,0,0.3)',overflow:'hidden'}}>
            <div style={{padding:'16px 20px',borderBottom:'1px solid '+cbb,display:'flex',alignItems:'center',gap:12}}>
              <div style={{flex:1}}>
                <div style={{fontSize:15,fontWeight:600,color:tc}}>Add Node</div>
                <div style={{fontSize:12,color:sc}}>Select vendor and device type</div>
              </div>
              <button onClick={()=>setAddNodeModal(null)} style={{background:'none',border:'none',fontSize:18,cursor:'pointer',color:sc}}>✕</button>
            </div>
            <div style={{display:'flex',flex:1,overflow:'hidden',minHeight:0}}>
              <div style={{width:140,background:darkMode?'#0f172a':'#f8fafc',borderRight:'1px solid '+cbb,overflowY:'auto',padding:'8px 0',flexShrink:0}}>
                {Object.keys(VENDOR_GROUPS).map(cat=>(
                  <div key={cat} onClick={()=>setActiveCategory(cat)}
                    style={{padding:'8px 14px',fontSize:12,cursor:'pointer',color:activeCategory===cat?tc:sc,background:activeCategory===cat?(darkMode?'#1e293b':'#eff6ff'):undefined,fontWeight:activeCategory===cat?600:400,borderLeft:activeCategory===cat?'2px solid #3b82f6':'2px solid transparent'}}>
                    {cat} <span style={{fontSize:10,color:sc}}>({VENDOR_GROUPS[cat].length})</span>
                  </div>
                ))}
              </div>
              <div style={{flex:1,overflowY:'auto',padding:12}}>
                <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:8}}>
                  {(VENDOR_GROUPS[activeCategory]||[]).map(([key,def])=>(
                    <div key={key} onClick={()=>addNodeToCanvas(key,addNodeModal)}
                      style={{display:'flex',alignItems:'center',gap:10,padding:'10px 12px',border:'1px solid '+cbb,borderRadius:8,cursor:'pointer',transition:'border-color 0.15s'}}
                      onMouseEnter={e=>e.currentTarget.style.borderColor=def.color}
                      onMouseLeave={e=>e.currentTarget.style.borderColor=cbb}>
                      <NodeIcon type={key} color={def.color} size={40}/>
                      <div style={{minWidth:0}}>
                        <div style={{fontSize:13,fontWeight:500,color:tc,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{def.label}</div>
                        <div style={{marginTop:2}}><VendorBadge vendor={def.vendor}/></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {addNetModal&&(
        <div style={{position:'fixed',inset:0,background:'rgba(0,0,0,0.45)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:2000}} onClick={()=>setAddNetModal(null)}>
          <div onClick={e=>e.stopPropagation()} style={{background:cb,borderRadius:12,padding:24,width:360,boxShadow:'0 20px 60px rgba(0,0,0,0.3)'}}>
            <div style={{fontSize:15,fontWeight:600,color:tc,marginBottom:16}}>Add Network Object</div>
            <div style={{display:'flex',flexDirection:'column',gap:8}}>
              {Object.entries(NET_DEFS).map(([key,def])=>(
                <div key={key} onClick={()=>{const name=prompt('Network name:',def.label);if(name){setNetworks(p=>[...p,{id:'net-'+Date.now(),name,type:key,x:addNetModal.x,y:addNetModal.y}]);setAddNetModal(null)}}}
                  style={{padding:'12px 16px',border:'1px solid '+cbb,borderRadius:8,cursor:'pointer'}}
                  onMouseEnter={e=>e.currentTarget.style.borderColor=def.color}
                  onMouseLeave={e=>e.currentTarget.style.borderColor=cbb}>
                  <div style={{fontSize:13,fontWeight:500,color:tc}}>{def.label}</div>
                  <div style={{fontSize:11,color:sc,marginTop:2}}>{key==='nat'?'Internet/NAT — DHCP + internet':key==='internal'?'Internal L2 — isolated segment':'Bridge — connects to host'}</div>
                </div>
              ))}
            </div>
            <button onClick={()=>setAddNetModal(null)} style={{marginTop:16,width:'100%',padding:'8px',border:'1px solid '+cbb,borderRadius:6,background:'transparent',color:sc,cursor:'pointer',fontSize:13}}>Cancel</button>
          </div>
        </div>
      )}

      {ifaceModal&&(()=>{
        const srcInfo = availableIfaces(ifaceModal.srcId)
        const dstInfo = ifaceModal.dstKind==='node' ? availableIfaces(ifaceModal.dstId) : {all:IFACES,used:new Set()}
        const srcNode2 = nodes.find(n=>n.id===ifaceModal.srcId)
        const dstNode2 = ifaceModal.dstKind==='node' ? nodes.find(n=>n.id===ifaceModal.dstId) : networks.find(n=>n.id===ifaceModal.dstId)
        const srcAvail = srcInfo.all.filter(i=>!srcInfo.used.has(i))
        const dstAvail = dstInfo.all.filter(i=>!dstInfo.used.has(i))
        return(
        <div style={{position:'fixed',inset:0,background:'rgba(0,0,0,0.45)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:2000}}>
          <div style={{background:cb,borderRadius:12,padding:24,width:460,boxShadow:'0 20px 60px rgba(0,0,0,0.3)'}}>
            <div style={{fontSize:15,fontWeight:600,color:tc,marginBottom:4}}>Configure Link</div>
            <div style={{fontSize:12,color:sc,marginBottom:16}}>Used interfaces shown in red and disabled</div>
            <div style={{display:'grid',gridTemplateColumns:'1fr 40px 1fr',gap:8,alignItems:'start',marginBottom:14}}>
              <div>
                <div style={{fontSize:11,fontWeight:600,color:tc,marginBottom:3}}>{srcNode2?.name||'Source'}</div>
                <div style={{fontSize:10,color:srcAvail.length===0?'#dc2626':'#16a34a',marginBottom:5}}>
                  {srcAvail.length}/{srcInfo.all.length} available
                </div>
                <select id="si" defaultValue={nextAvailableIface(ifaceModal.srcId)} style={{width:'100%',padding:'7px 8px',border:'1px solid '+(srcAvail.length===0?'#dc2626':cbb),borderRadius:6,fontSize:11,background:cb,color:tc}}>
                  {srcInfo.all.map(i=>{const used=srcInfo.used.has(i);return(
                    <option key={i} value={i} disabled={used} style={{color:used?'#9ca3af':tc}}>
                      {used?'✗ [in use] ':''}{i}
                    </option>
                  )})}
                </select>
              </div>
              <div style={{textAlign:'center',fontSize:18,color:sc,paddingTop:32}}>⟷</div>
              <div>
                <div style={{fontSize:11,fontWeight:600,color:tc,marginBottom:3}}>{dstNode2?.name||'Destination'}</div>
                <div style={{fontSize:10,color:dstAvail.length===0?'#dc2626':'#16a34a',marginBottom:5}}>
                  {dstAvail.length}/{dstInfo.all.length} available
                </div>
                <select id="di" defaultValue={ifaceModal.dstKind==='node'?nextAvailableIface(ifaceModal.dstId):'eth0'} style={{width:'100%',padding:'7px 8px',border:'1px solid '+(dstAvail.length===0?'#dc2626':cbb),borderRadius:6,fontSize:11,background:cb,color:tc}}>
                  {dstInfo.all.map(i=>{const used=dstInfo.used.has(i);return(
                    <option key={i} value={i} disabled={used} style={{color:used?'#9ca3af':tc}}>
                      {used?'✗ [in use] ':''}{i}
                    </option>
                  )})}
                </select>
              </div>
            </div>
            <div style={{background:darkMode?'#0f172a':'#f8fafc',borderRadius:6,padding:'6px 10px',marginBottom:14,fontSize:11,color:sc,display:'flex',alignItems:'center',gap:6}}>
              <span style={{color:'#f59e0b'}}>⚠</span> Each interface can only be connected once
            </div>
            <div style={{display:'flex',gap:8,justifyContent:'flex-end'}}>
              <button onClick={()=>setIfaceModal(null)} style={{padding:'8px 18px',border:'1px solid '+cbb,borderRadius:6,background:'transparent',color:sc,cursor:'pointer',fontSize:13}}>Cancel</button>
              <button
                onClick={()=>{
                  const si=document.getElementById('si').value
                  const di=document.getElementById('di').value
                  if(srcInfo.used.has(si)){alert(si+' is already in use on '+srcNode2?.name);return}
                  if(dstInfo.used.has(di)){alert(di+' is already in use on '+dstNode2?.name);return}
                  finishLink(si,di)
                }}
                disabled={srcAvail.length===0||dstAvail.length===0}
                style={{padding:'8px 18px',background:srcAvail.length===0||dstAvail.length===0?'#9ca3af':'#2563eb',color:'white',border:'none',borderRadius:6,cursor:srcAvail.length===0||dstAvail.length===0?'not-allowed':'pointer',fontSize:13,fontWeight:500}}>
                Connect
              </button>
            </div>
          </div>
        </div>
        )
      })()}


      {pendingAdd&&(
        <div style={{position:'fixed',inset:0,background:'rgba(0,0,0,0.55)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:3000}}>
          <div style={{background:cb,borderRadius:12,padding:28,width:420,boxShadow:'0 20px 60px rgba(0,0,0,0.4)',border:'1px solid '+cbb}}>
            <div style={{display:'flex',alignItems:'center',gap:14,marginBottom:20,paddingBottom:16,borderBottom:'1px solid '+cbb}}>
              <NodeIcon type={pendingAdd.vendorType} color={VENDORS[pendingAdd.vendorType]?.color} size={44} muted={false}/>
              <div>
                <div style={{fontSize:15,fontWeight:600,color:tc}}>{VENDORS[pendingAdd.vendorType]?.label||'Node'}</div>
                <VendorBadge vendor={VENDORS[pendingAdd.vendorType]?.vendor||'Generic'}/>
              </div>
              <button onClick={()=>setPendingAdd(null)} style={{marginLeft:'auto',background:'none',border:'none',fontSize:18,cursor:'pointer',color:sc}}>✕</button>
            </div>
            <div style={{display:'flex',flexDirection:'column',gap:16,marginBottom:20}}>
              <div>
                <label style={{fontSize:12,fontWeight:500,color:sc,display:'block',marginBottom:8}}>How many nodes?</label>
                <div style={{display:'flex',alignItems:'center',gap:10}}>
                  <button onClick={()=>setQty(q=>Math.max(1,q-1))} style={{width:34,height:34,border:'1px solid '+cbb,borderRadius:6,background:'transparent',color:tc,fontSize:20,cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center'}}>−</button>
                  <input type="number" min="1" max="20" value={qty}
                    onChange={e=>setQty(Math.min(20,Math.max(1,parseInt(e.target.value)||1)))}
                    style={{width:64,textAlign:'center',padding:'7px',border:'1px solid '+cbb,borderRadius:6,background:darkMode?'#0f172a':'#f8fafc',color:tc,fontSize:18,fontWeight:700}}/>
                  <button onClick={()=>setQty(q=>Math.min(20,q+1))} style={{width:34,height:34,border:'1px solid '+cbb,borderRadius:6,background:'transparent',color:tc,fontSize:20,cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center'}}>+</button>
                  <div style={{display:'flex',gap:4}}>
                    {[1,2,4,6,8,10].map(n=>{
                      const ac=VENDORS[pendingAdd.vendorType]?.color||'#3b82f6'
                      return <button key={n} onClick={()=>setQty(n)}
                        style={{padding:'5px 9px',border:'1px solid '+(qty===n?ac:cbb),borderRadius:4,background:qty===n?ac+'22':'transparent',color:qty===n?ac:sc,fontSize:12,cursor:'pointer',fontWeight:qty===n?600:400}}>{n}</button>
                    })}
                  </div>
                </div>
              </div>
              <div style={{display:'grid',gridTemplateColumns:qty>1?'2fr 1fr':'1fr',gap:10}}>
                <div>
                  <label style={{fontSize:12,fontWeight:500,color:sc,display:'block',marginBottom:6}}>{qty===1?'Node name':'Name prefix'}</label>
                  <input value={nodePrefix}
                    onChange={e=>setNodePrefix(e.target.value)}
                    placeholder={(VENDORS[pendingAdd.vendorType]?.label||'Node')+(qty>1?'-':'-1')}
                    style={{width:'100%',padding:'8px 10px',border:'1px solid '+cbb,borderRadius:6,background:darkMode?'#0f172a':'#f8fafc',color:tc,fontSize:13,boxSizing:'border-box',outline:'none'}}
                    onFocus={e=>e.target.style.borderColor=VENDORS[pendingAdd.vendorType]?.color||'#3b82f6'}
                    onBlur={e=>e.target.style.borderColor=cbb}/>
                </div>
                {qty>1&&<div>
                  <label style={{fontSize:12,fontWeight:500,color:sc,display:'block',marginBottom:6}}>Start #</label>
                  <input type="number" min="0" value={startNum}
                    onChange={e=>setStartNum(parseInt(e.target.value)||1)}
                    style={{width:'100%',padding:'8px 10px',border:'1px solid '+cbb,borderRadius:6,background:darkMode?'#0f172a':'#f8fafc',color:tc,fontSize:13,boxSizing:'border-box'}}/>
                </div>}
              </div>
              {qty>1&&(
                <div style={{background:darkMode?'#0f172a':'#f8fafc',border:'1px solid '+cbb,borderRadius:8,padding:'10px 14px'}}>
                  <div style={{fontSize:11,color:sc,marginBottom:4}}>Preview ({qty} nodes, {Math.ceil(qty/4)} row{Math.ceil(qty/4)>1?'s':''})</div>
                  <div style={{fontSize:12,color:tc,fontFamily:'monospace'}}>
                    {Array.from({length:Math.min(qty,5)},(_,i)=>(nodePrefix||(VENDORS[pendingAdd.vendorType]?.label||'Node')+'-')+(startNum+i)).join(', ')}{qty>5?', ...':''}
                  </div>
                </div>
              )}
            </div>
            <div style={{display:'flex',gap:8,justifyContent:'flex-end'}}>
              <button onClick={()=>setPendingAdd(null)} style={{padding:'9px 20px',border:'1px solid '+cbb,borderRadius:6,background:'transparent',color:sc,cursor:'pointer',fontSize:13}}>Cancel</button>
              <button onClick={confirmAddNodes}
                style={{padding:'9px 20px',background:VENDORS[pendingAdd.vendorType]?.color||'#2563eb',color:'white',border:'none',borderRadius:6,cursor:'pointer',fontSize:13,fontWeight:600}}>
                Add {qty} Node{qty!==1?'s':''}
              </button>
            </div>
          </div>
        </div>
      )}

      {confirmDel&&(
        <div style={{position:'fixed',left:Math.min(confirmDel.pos.x,window.innerWidth-280),top:Math.min(confirmDel.pos.y-20,window.innerHeight-120),zIndex:9999,background:'#1e293b',border:'1px solid #f87171',borderRadius:10,padding:'14px 18px',boxShadow:'0 8px 32px rgba(0,0,0,0.5)',minWidth:240,fontFamily:'sans-serif'}}>
          <div style={{fontSize:14,fontWeight:600,color:'#f1f5f9',marginBottom:10}}>
            Delete {confirmDel.toDelete.size} node{confirmDel.toDelete.size>1?'s':''}?
          </div>
          <div style={{fontSize:12,color:'#94a3b8',marginBottom:14}}>This cannot be undone.</div>
          <div style={{display:'flex',gap:8}}>
            <button onClick={()=>setConfirmDel(null)}
              style={{flex:1,padding:'7px',border:'1px solid #475569',borderRadius:6,background:'transparent',color:'#94a3b8',cursor:'pointer',fontSize:13}}>
              Cancel
            </button>
            <button onClick={()=>{
              confirmDel.toDelete.forEach(id=>deleteNode(id).catch(()=>{}))
              setNodes(p=>p.filter(n=>!confirmDel.toDelete.has(n.id)))
              setLinks(p=>p.filter(l=>!confirmDel.toDelete.has(l.srcId)&&!confirmDel.toDelete.has(l.dstId)))
              const ns=new Set(); selectedRef.current=ns; setSelected(ns)
              setConfirmDel(null)
            }}
              style={{flex:1,padding:'7px',border:'none',borderRadius:6,background:'#dc2626',color:'white',cursor:'pointer',fontSize:13,fontWeight:600}}>
              Delete
            </button>
          </div>
        </div>
      )}
      {selectedNode && (
        <div style={{position:'fixed',top:0,right:0,bottom:0,zIndex:1000,boxShadow:'-8px 0 24px rgba(0,0,0,.4)'}}>
          <NodePanel
            node={selectedNode}
            labId={labId}
            onClose={()=>setSelectedNode(null)}
            onSaved={(id,{name,config})=>{
              setNodes(p=>p.map(n=>n.id===id?{...n,name:name||n.name,config:config!==undefined?config:n.config}:n))
            }}
          />
        </div>
      )}
      {/* CRE-68: Traffic Filter Panel */}
      {showTrafficFilters && (
        <TrafficFilterPanel
          labId={labId}
          darkMode={darkMode}
          onClose={()=>setShowTrafficFilters(false)}
          wsConnected={wsConnected}
          packetCounts={packetCounts}
          wsError={wsLastError}
        />
      )}
    </div>
  )
}
