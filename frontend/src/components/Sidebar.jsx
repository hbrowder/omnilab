import React, { useEffect, useState, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { getLabs, getSystemInfo, createLab, deleteLab as apiDeleteLab, exportLab as apiExportLab, importLab as apiImportLab } from '../utils/api'
import { useStore } from '../store'

const NAV = [
  { icon:'▦', label:'Dashboard', path:'/' },
  { icon:'🧪', label:'Templates', path:'/templates' },
  { icon:'⚙', label:'System',    path:'/system' },
  { icon:'📊', label:'Health',    path:'/health' },
]

const CAT_COLORS = {
  security:'#f85149', devops:'#3fb950',
  'ai-ml':'#a371f7', networking:'#58a6ff', general:'#8b949e'
}

function OmniLogo() {
  return (
    <svg width="36" height="36" viewBox="0 0 32 32" style={{flexShrink:0}}>
      <ellipse cx="16" cy="16" rx="14" ry="5.5" fill="none" stroke="#bfdbfe" strokeWidth="2" transform="rotate(-25 16 16)"/>
      <ellipse cx="16" cy="16" rx="14" ry="5.5" fill="none" stroke="#3b82f6" strokeWidth="2" transform="rotate(35 16 16)"/>
      <ellipse cx="16" cy="16" rx="14" ry="5.5" fill="none" stroke="#1d4ed8" strokeWidth="2" transform="rotate(95 16 16)"/>
      <circle cx="16" cy="16" r="5" fill="#1d4ed8"/>
      <text x="16" y="19.5" fontFamily="Arial,sans-serif" fontSize="7" fontWeight="800" fill="white" textAnchor="middle">O</text>
    </svg>
  )
}

const FOLDERS_KEY = 'omnilab_folders'
const loadFolders = () => { try { return JSON.parse(localStorage.getItem(FOLDERS_KEY)) || [] } catch { return [] } }
const saveFolders = f => localStorage.setItem(FOLDERS_KEY, JSON.stringify(f))

export default function Sidebar({ onLogout }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { labs, setLabs, setSystemInfo } = useStore()
  const removeLab = useStore(s => s.removeLab)
  const importFileInputRef = useRef(null)
  const handleExportLab = async (lab) => {
    try {
      const res = await apiExportLab(lab.id)
      const bundle = res.data
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      const safeName = (lab.name || 'lab').replace(/[^a-z0-9-_]+/gi, '_')
      a.href = url
      a.download = safeName + '.omnilab.json'
      document.body.appendChild(a); a.click(); document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) { console.error('exportLab failed', e); alert('Export failed: ' + (e.message || e)) }
  }
  const handleImportLab = () => {
    if (importFileInputRef.current) importFileInputRef.current.click()
  }
  const handleImportFile = async (ev) => {
    const file = ev.target.files && ev.target.files[0]
    ev.target.value = ''
    if (!file) return
    try {
      const text = await file.text()
      const bundle = JSON.parse(text)
      const res = await apiImportLab(bundle)
      const l2 = await getLabs()
      setLabs(l2.data)
      if (res && res.data && res.data.id) navigate('/lab/' + res.data.id)
    } catch (e) { console.error('importLab failed', e); alert('Import failed: ' + (e.message || e)) }
  }
  const [folders, setFolders] = useState(loadFolders)
  const [expanded, setExpanded] = useState({})
  const [ctxMenu, setCtxMenu] = useState(null)
  const [confirmingDelete, setConfirmingDelete] = useState(null)
  const [renamingId, setRenamingId] = useState(null)
  const [dragLabId, setDragLabId] = useState(null)
  const [dragOver, setDragOver] = useState(null) // folderId or 'root'

  useEffect(() => { getLabs().then(r => setLabs(r.data)).catch(() => {}) }, [])
  useEffect(() => { saveFolders(folders) }, [folders])
  useEffect(() => {
    const close = () => setCtxMenu(null)
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [])

  const createFolder = (parentId = null) => {
    const id = 'folder-' + Date.now()
    setFolders(f => [...f, { id, name:'New Folder', parentId, labIds:[] }])
    setExpanded(e => ({...e, [id]: true}))
    setRenamingId(id)
  }

  const deleteFolder = id => {
    setFolders(f => f.filter(x => x.id !== id))
  }

  const renameFolder = (id, val) => {
    if (val.trim()) setFolders(f => f.map(x => x.id === id ? {...x, name:val.trim()} : x))
    setRenamingId(null)
  }

  const moveLab = (labId, folderId) => {
    setFolders(f => f.map(x => ({
      ...x,
      labIds: folderId === x.id
        ? [...new Set([...x.labIds, labId])]
        : x.labIds.filter(id => id !== labId)
    })))
  }

  const removeLabFromFolder = labId => {
    setFolders(f => f.map(x => ({...x, labIds: x.labIds.filter(id => id !== labId)})))
  }

  const getLabFolder = labId => folders.find(f => f.labIds.includes(labId))

  // Drag handlers
  const onLabDragStart = (e, labId) => {
    setDragLabId(labId)
    e.dataTransfer.effectAllowed = 'move'
  }
  const onLabDragEnd = () => { setDragLabId(null); setDragOver(null) }

  const onFolderDragOver = (e, folderId) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOver(folderId)
  }
  const onFolderDrop = (e, folderId) => {
    e.preventDefault()
    if (dragLabId) {
      if (folderId === 'root') removeLabFromFolder(dragLabId)
      else moveLab(dragLabId, folderId)
    }
    setDragOver(null)
    setDragLabId(null)
  }

  const showCtx = (e, type, data) => {
    e.preventDefault(); e.stopPropagation()
    setCtxMenu({ x:e.clientX, y:e.clientY, type, data })
  }

  const rootFolders = folders.filter(f => !f.parentId)
  const rootLabs = labs.filter(l => !getLabFolder(l.id))

  const LabItem = ({ lab, indent=0 }) => {
    const isActive = location.pathname === '/lab/'+lab.id
    return (
      <div
        draggable
        onDragStart={e => onLabDragStart(e, lab.id)}
        onDragEnd={onLabDragEnd}
        onClick={() => navigate('/lab/'+lab.id)}
        onContextMenu={e => showCtx(e, 'lab', lab)}
        style={{
          display:'flex', alignItems:'center', gap:8,
          padding:'6px 16px 6px '+(16+indent*12)+'px',
          cursor:'grab', fontSize:13,
          color: isActive ? '#e6edf3' : '#8b949e',
          background: isActive ? '#1f2937' : dragLabId===lab.id?'#1e293b':'transparent',
          borderLeft: isActive ? '2px solid #58a6ff' : '2px solid transparent',
          opacity: dragLabId===lab.id ? 0.5 : 1,
        }}
        onMouseEnter={e=>{ if(!isActive) e.currentTarget.style.background='#161b22' }}
        onMouseLeave={e=>{ if(!isActive) e.currentTarget.style.background=dragLabId===lab.id?'#1e293b':'transparent' }}>
        <div style={{width:7,height:7,borderRadius:'50%',background:CAT_COLORS[lab.category]||'#8b949e',flexShrink:0}}/>
        <span style={{overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',flex:1}}>{lab.name}</span>
        <span style={{fontSize:9,color:'#484f58',flexShrink:0}} title="Drag to folder">⠿</span>
      </div>
    )
  }

  const FolderItem = ({ folder, depth=0 }) => {
    const isOpen = expanded[folder.id]
    const folderLabs = labs.filter(l => folder.labIds.includes(l.id))
    const subFolders = folders.filter(f => f.parentId === folder.id)
    const isDragTarget = dragOver === folder.id

    return (
      <div
        onDragOver={e => onFolderDragOver(e, folder.id)}
        onDragLeave={() => setDragOver(null)}
        onDrop={e => onFolderDrop(e, folder.id)}>
        <div
          onClick={() => setExpanded(e => ({...e, [folder.id]: !e[folder.id]}))}
          onContextMenu={e => showCtx(e, 'folder', folder)}
          style={{
            display:'flex', alignItems:'center', gap:6,
            padding:'6px 16px 6px '+(16+depth*12)+'px',
            cursor:'pointer', fontSize:13, color:'#8b949e',
            background: isDragTarget ? '#1e3a5f' : 'transparent',
            borderLeft: isDragTarget ? '2px solid #3b82f6' : '2px solid transparent',
            borderRadius: isDragTarget ? '0 4px 4px 0' : 0,
          }}
          onMouseEnter={e=>{ if(!isDragTarget) e.currentTarget.style.background='#161b22' }}
          onMouseLeave={e=>{ if(!isDragTarget) e.currentTarget.style.background='transparent' }}>
          <span style={{fontSize:10,color:'#484f58',width:10,flexShrink:0}}>{isOpen?'▼':'▶'}</span>
          <span style={{fontSize:14,flexShrink:0}}>{isDragTarget?'📂':'📁'}</span>
          {renamingId === folder.id ? (
            <input autoFocus defaultValue={folder.name}
              onBlur={e => renameFolder(folder.id, e.target.value)}
              onKeyDown={e => { e.stopPropagation(); if(e.key==='Enter') renameFolder(folder.id, e.target.value); if(e.key==='Escape') setRenamingId(null) }}
              onClick={e => e.stopPropagation()}
              style={{flex:1,background:'#21262d',border:'1px solid #3b82f6',borderRadius:4,padding:'1px 6px',color:'#e6edf3',fontSize:12,outline:'none'}}/>
          ) : (
            <span style={{flex:1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{folder.name}</span>
          )}
          {folderLabs.length > 0 && <span style={{fontSize:10,color:'#484f58',flexShrink:0}}>{folderLabs.length}</span>}
        </div>
        {isOpen && (
          <div>
            {subFolders.map(sf => <FolderItem key={sf.id} folder={sf} depth={depth+1}/>)}
            {folderLabs.map(lab => <LabItem key={lab.id} lab={lab} indent={depth+1}/>)}
            {folderLabs.length===0 && subFolders.length===0 && (
              <div style={{padding:'3px 16px 3px '+(28+depth*12)+'px',fontSize:11,color:isDragTarget?'#3b82f6':'#30363d',fontStyle:'italic'}}>
                {isDragTarget?'Drop here':'Empty folder'}
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{width:240,background:'#0d1117',borderRight:'1px solid #21262d',display:'flex',flexDirection:'column',flexShrink:0,position:'relative'}}>

      {/* Logo */}
      <div style={{padding:'18px 16px 14px',borderBottom:'1px solid #21262d'}}>
        <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:6}}>
          <OmniLogo/>
          <div>
            <div style={{display:'flex',alignItems:'baseline'}}>
              <span style={{fontWeight:800,fontSize:17,color:'#ffffff',letterSpacing:'-0.5px',fontFamily:'system-ui,sans-serif'}}>OMNI</span>
              <span style={{fontWeight:800,fontSize:17,color:'#6b7280',letterSpacing:'4px',fontFamily:'system-ui,sans-serif'}}>LAB</span>
            </div>
            <div style={{fontSize:9,color:'#3b82f6',letterSpacing:'0.5px',fontFamily:'monospace',marginTop:1}}>OPEN MULTI-NODE INFRA</div>
          </div>
        </div>
        <div style={{fontSize:10,color:'#484f58',fontStyle:'italic'}}>Every node. Every stack. One lab.</div>
      </div>

      {/* Nav */}
      <div style={{padding:'8px 0',borderBottom:'1px solid #21262d'}}>
        {NAV.map(item => (
          <div key={item.path} onClick={() => navigate(item.path)}
            style={{display:'flex',alignItems:'center',gap:10,padding:'8px 16px',cursor:'pointer',fontSize:13,
              color: location.pathname===item.path?'#58a6ff':'#8b949e',
              background: location.pathname===item.path?'#1f2937':'transparent',
              borderLeft: location.pathname===item.path?'2px solid #58a6ff':'2px solid transparent'}}
            onMouseEnter={e=>e.currentTarget.style.background='#161b22'}
            onMouseLeave={e=>e.currentTarget.style.background=location.pathname===item.path?'#1f2937':'transparent'}>
            <span style={{fontSize:16}}>{item.icon}</span>{item.label}
          </div>
        ))}
      </div>

      {/* Labs + Folders */}
      <div style={{flex:1,overflow:'auto',display:'flex',flexDirection:'column'}}>
        {/* Root drop zone */}
        <div
          onDragOver={e=>onFolderDragOver(e,'root')}
          onDragLeave={()=>setDragOver(null)}
          onDrop={e=>onFolderDrop(e,'root')}>
          <div style={{padding:'8px 16px 6px',display:'flex',alignItems:'center',justifyContent:'space-between'}}
            onContextMenu={e=>showCtx(e,'labs-root',null)}>
            <span style={{fontSize:11,fontWeight:600,color: dragOver==='root'?'#3b82f6':'#8b949e',textTransform:'uppercase',letterSpacing:'0.5px'}}>
              Labs ({labs.length}) {dragOver==='root'?'— drop to ungroup':''}
            </span>
            <div style={{display:'flex',gap:4}}>
              <button title="New Folder" onClick={e=>{e.stopPropagation();createFolder(null)}}
                style={{background:'transparent',border:'none',color:'#484f58',cursor:'pointer',fontSize:13,padding:'0 3px'}}
                onMouseEnter={e=>e.currentTarget.style.color='#8b949e'}
                onMouseLeave={e=>e.currentTarget.style.color='#484f58'}>📁+</button>
              <button title="New Lab" onClick={async e=>{
                e.stopPropagation()
                const name=prompt('Lab name:'); if(!name) return
                try{ const r=await createLab({name,category:'general'}); const l2=await getLabs(); setLabs(l2.data); navigate('/lab/'+r.data.id) }catch{}
              }}
                style={{background:'transparent',border:'none',color:'#484f58',cursor:'pointer',fontSize:16,padding:'0 3px'}}
                onMouseEnter={e=>e.currentTarget.style.color='#8b949e'}
                onMouseLeave={e=>e.currentTarget.style.color='#484f58'}>+</button>
            <button title="Import Lab" onClick={e=>{e.stopPropagation();handleImportLab()}} style={{background:'transparent',border:'none',color:'#8b949e',fontSize:14,cursor:'pointer',padding:'2px 4px'}}>⇩</button>
            <input ref={importFileInputRef} type="file" accept=".json,application/json" onChange={handleImportFile} style={{display:'none'}} />
            </div>
          </div>
        </div>

        <div style={{flex:1,overflow:'auto'}}>
          {rootFolders.map(f => <FolderItem key={f.id} folder={f} depth={0}/>)}
          {rootLabs.map(lab => <LabItem key={lab.id} lab={lab} indent={0}/>)}
          {labs.length===0 && folders.length===0 && (
            <div style={{padding:'8px 16px',fontSize:12,color:'#484f58',fontStyle:'italic'}}>
              Right-click to create a folder
            </div>
          )}
          {dragLabId && (
            <div style={{padding:'6px 16px',fontSize:11,color:'#484f58',textAlign:'center',borderTop:'1px dashed #21262d',marginTop:4}}>
              ↑ Drop above to remove from folder
            </div>
          )}
        </div>
      </div>

      {/* Bottom: status + logout */}
      <div style={{borderTop:'1px solid #21262d'}}>
        <div style={{padding:'8px 16px',display:'flex',alignItems:'center',justifyContent:'space-between'}}>
          <div style={{display:'flex',alignItems:'center',gap:6,fontSize:11,color:'#3fb950'}}>
            <div style={{width:6,height:6,borderRadius:'50%',background:'#3fb950'}}/>
            Backend online
          </div>
          <button onClick={onLogout}
            title="Sign out"
            style={{background:'transparent',border:'1px solid #21262d',borderRadius:5,color:'#8b949e',cursor:'pointer',fontSize:11,padding:'3px 8px',display:'flex',alignItems:'center',gap:4}}
            onMouseEnter={e=>{e.currentTarget.style.borderColor='#f85149';e.currentTarget.style.color='#f85149'}}
            onMouseLeave={e=>{e.currentTarget.style.borderColor='#21262d';e.currentTarget.style.color='#8b949e'}}>
            ⏻ Sign out
          </button>
        </div>
        <div style={{padding:'0 16px 8px',fontSize:9,color:'#30363d'}}>v1.0.0 — Free Tier</div>
      </div>

      {/* Delete-lab confirm */}
      {confirmingDelete && (
        <div onClick={()=>setConfirmingDelete(null)} style={{
          position:'fixed', inset:0, background:'rgba(0,0,0,0.55)',
          display:'flex', alignItems:'center', justifyContent:'center', zIndex:10000
        }}>
          <div onClick={e=>e.stopPropagation()} style={{
            background:'#161b22', border:'1px solid #30363d', borderRadius:10,
            padding:'20px 22px', minWidth:340, maxWidth:420,
            boxShadow:'0 12px 40px rgba(0,0,0,0.6)', color:'#e6edf3'
          }}>
            <div style={{fontSize:15, fontWeight:600, marginBottom:8, color:'#f85149'}}>
              Delete lab?
            </div>
            <div style={{fontSize:13, color:'#8b949e', marginBottom:16, lineHeight:1.5}}>
              This will permanently delete <span style={{color:'#e6edf3', fontWeight:600}}>{confirmingDelete.name}</span> and all of its nodes and links. This cannot be undone.
            </div>
            <div style={{display:'flex', gap:8, justifyContent:'flex-end'}}>
              <button onClick={()=>setConfirmingDelete(null)} style={{
                background:'transparent', border:'1px solid #30363d', color:'#e6edf3',
                padding:'7px 14px', borderRadius:6, fontSize:13, cursor:'pointer'
              }}>Cancel</button>
              <button onClick={async ()=>{
                const id = confirmingDelete.id
                const onLabPage = window.location.pathname === '/lab/'+id
                try { await apiDeleteLab(id) } catch(e) { console.error('deleteLab failed', e) }
                if (removeLab) removeLab(id)
                setConfirmingDelete(null)
                if (onLabPage) navigate('/')
              }} style={{
                background:'#f85149', border:'1px solid #f85149', color:'#fff',
                padding:'7px 14px', borderRadius:6, fontSize:13, fontWeight:600, cursor:'pointer'
              }}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Context menu */}
      {ctxMenu && (
        <div onClick={e=>e.stopPropagation()} style={{
          position:'fixed',left:Math.min(ctxMenu.x,window.innerWidth-200),top:Math.min(ctxMenu.y,window.innerHeight-280),
          background:'#161b22',border:'1px solid #30363d',borderRadius:8,
          boxShadow:'0 8px 32px rgba(0,0,0,0.5)',zIndex:9999,minWidth:190,overflow:'hidden'}}>

          {ctxMenu.type==='labs-root' && [
            {l:'📁  New Folder', a:()=>{createFolder(null);setCtxMenu(null)}},
            {l:'🧪  New Lab',    a:async()=>{ const name=prompt('Lab name:'); if(!name) return; try{const r=await createLab({name,category:'general'});const l2=await getLabs();setLabs(l2.data);navigate('/lab/'+r.data.id)}catch{} setCtxMenu(null) }},
          
          {l:'📥  Import Lab…', a:()=>{ setCtxMenu(null); handleImportLab() }},
        ].map(item=>(
            <div key={item.l} onClick={item.a}
              style={{padding:'9px 16px',fontSize:13,color:'#e6edf3',cursor:'pointer',borderBottom:'1px solid #21262d'}}
              onMouseEnter={e=>e.currentTarget.style.background='#1f2937'}
              onMouseLeave={e=>e.currentTarget.style.background='transparent'}>{item.l}</div>
          ))}

          {ctxMenu.type==='folder' && [
            {l:'📁  New Subfolder', a:()=>{createFolder(ctxMenu.data.id);setCtxMenu(null)}},
            {l:'🧪  New Lab Here',  a:async()=>{ const name=prompt('Lab name:'); if(!name) return; try{const r=await createLab({name,category:'general'});const l2=await getLabs();setLabs(l2.data);moveLab(r.data.id,ctxMenu.data.id);navigate('/lab/'+r.data.id)}catch{} setCtxMenu(null) }},
            {l:'✎  Rename',         a:()=>{setRenamingId(ctxMenu.data.id);setCtxMenu(null)}},
            {l:'🗑  Delete Folder', col:'#f85149', a:()=>{deleteFolder(ctxMenu.data.id);setCtxMenu(null)}},
          ].map(item=>(
            <div key={item.l} onClick={item.a}
              style={{padding:'9px 16px',fontSize:13,color:item.col||'#e6edf3',cursor:'pointer',borderBottom:'1px solid #21262d'}}
              onMouseEnter={e=>e.currentTarget.style.background='#1f2937'}
              onMouseLeave={e=>e.currentTarget.style.background='transparent'}>{item.l}</div>
          ))}

          {ctxMenu.type==='lab' && (()=>{
            const cur = getLabFolder(ctxMenu.data.id)
            return [
              {l:'▶  Open Lab', a:()=>{navigate('/lab/'+ctxMenu.data.id);setCtxMenu(null)}},
              {l:'📁  Move to Folder…', a:()=>{
                const opts=['(No folder)',...folders.map(f=>f.name)]
                const choice=prompt('Move to folder:\n'+opts.map((o,i)=>i+'. '+o).join('\n')+'\n\nEnter number:')
                if(choice===null) return
                const idx=parseInt(choice)
                if(idx===0) removeLabFromFolder(ctxMenu.data.id)
                else if(folders[idx-1]) moveLab(ctxMenu.data.id,folders[idx-1].id)
                setCtxMenu(null)
              }},
              cur && {l:'↑  Remove from Folder', a:()=>{removeLabFromFolder(ctxMenu.data.id);setCtxMenu(null)}},
                  {l:'🗑  Delete Lab', col:'#f85149', a:()=>{ setConfirmingDelete(ctxMenu.data); setCtxMenu(null); }},
            {l:'↗  Export Lab', a:()=>{ handleExportLab(ctxMenu.data); setCtxMenu(null); }},
      ].filter(Boolean).map(item=>(
              <div key={item.l} onClick={item.a}
                style={{padding:'9px 16px',fontSize:13,color:'#e6edf3',cursor:'pointer',borderBottom:'1px solid #21262d'}}
                onMouseEnter={e=>e.currentTarget.style.background='#1f2937'}
                onMouseLeave={e=>e.currentTarget.style.background='transparent'}>{item.l}</div>
            ))
          })()}
        </div>
      )}
    </div>
  )
}
