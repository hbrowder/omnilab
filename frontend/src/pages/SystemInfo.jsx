import React, { useEffect, useState } from 'react'
import { useStore } from '../store'
import { getSystemInfo, getAIProvider, saveAIProvider, testAIProvider } from '../utils/api'
import RunHistory from '../components/AIBuilder/RunHistory'
import AIBuilderPanel from '../components/AIBuilder/AIBuilderPanel'

// Per-provider sensible model defaults — mirror backend services/ai_provider.py.
const PROVIDER_DEFAULTS = {
  openrouter: { label: 'OpenRouter', model: 'anthropic/claude-sonnet-4.5', custom: false },
  anthropic:  { label: 'Anthropic',  model: 'claude-sonnet-4-5',           custom: false },
  openai:     { label: 'OpenAI',     model: 'gpt-4o',                      custom: false },
  custom:     { label: 'Custom (OpenAI-compatible)', model: '',            custom: true },
}

export default function SystemInfo() {
  const { systemInfo, setSystemInfo } = useStore()
  const [aiOpen, setAiOpen] = useState(false)
  const [rerunPrompt, setRerunPrompt] = useState(null)
  useEffect(() => { getSystemInfo().then(r=>setSystemInfo(r.data)).catch(()=>{}) }, [])
  const handleRerun = (prompt) => { setRerunPrompt(prompt); setAiOpen(true) }
  const info = systemInfo || {}
  const CHECKS = [
    { label:'KVM / Hardware Virtualization', value:info.kvm_available },
    { label:'QEMU Binary', value:info.qemu_available },
    { label:'Docker Engine', value:info.docker_available },
    { label:'Open vSwitch', value:info.ovs_available },
  ]

  // --- CRE-45: AI Lab Builder (BYO-key) provider config ---
  const [ai, setAi] = useState(null)          // GET result (never has the key)
  const [provider, setProvider] = useState('openrouter')
  const [apiKey, setApiKey] = useState('')     // write-only; cleared after save
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const [savedMsg, setSavedMsg] = useState('')
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  const loadAI = () => getAIProvider().then(r => {
    setAi(r.data)
    setProvider(r.data.provider || 'openrouter')
    setModel(r.data.model || '')
    setBaseUrl(r.data.base_url || '')
  }).catch(()=>{})
  useEffect(() => { loadAI() }, [])

  const onProviderChange = (p) => {
    setProvider(p)
    // Apply the per-provider default model when switching.
    setModel(PROVIDER_DEFAULTS[p]?.model || '')
    if (!PROVIDER_DEFAULTS[p]?.custom) setBaseUrl('')
  }

  const onSave = async () => {
    setSaving(true); setSavedMsg(''); setTestResult(null)
    try {
      const body = { provider, model }
      if (PROVIDER_DEFAULTS[provider]?.custom) body.base_url = baseUrl
      // Only send the api_key if the operator typed one (write-only).
      if (apiKey) body.api_key = apiKey
      const r = await saveAIProvider(body)
      setAi(r.data)
      setApiKey('')                 // never keep the key in the field
      setSavedMsg('Saved.')
    } catch (e) {
      setSavedMsg('Save failed: ' + (e?.response?.data?.detail || e.message))
    } finally {
      setSaving(false)
    }
  }

  const onTest = async () => {
    setTesting(true); setTestResult(null)
    try {
      const r = await testAIProvider()
      setTestResult(r.data)
    } catch (e) {
      setTestResult({ ok:false, error: e?.response?.data?.detail || e.message })
    } finally {
      setTesting(false)
    }
  }

  const inputStyle = { width:'100%', boxSizing:'border-box', padding:'8px 10px', background:'#0d1117', border:'1px solid #30363d', borderRadius:6, color:'#e6edf3', fontSize:13 }
  const labelStyle = { fontSize:12, color:'#8b949e', marginBottom:4, display:'block' }
  const keyConfigured = ai?.api_key_set
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
      <div style={{ background:'#161b22', border:'1px solid #21262d', borderRadius:10, padding:16, marginBottom:16 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:4 }}>
          <div style={{ fontSize:14, fontWeight:600, color:'#e6edf3' }}>AI Lab Builder</div>
          <span style={{ fontSize:12, padding:'2px 10px', borderRadius:12, background:keyConfigured?'#1a3a1a':'#3a2a1a', color:keyConfigured?'#3fb950':'#d29922' }}>
            {ai===null ? '…' : keyConfigured ? '✓ configured' : 'not configured'}
          </span>
        </div>
        <div style={{ fontSize:12, color:'#8b949e', marginBottom:14 }}>
          {keyConfigured
            ? <>The lab builder uses your stored API key.{ai?.last4 ? <> (key ending <code style={{ color:'#58a6ff' }}>…{ai.last4}</code>)</> : null}</>
            : 'Configure your AI provider to enable the AI lab builder. Bring your own key — it is encrypted at rest and never leaves this machine.'}
        </div>

        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginBottom:12 }}>
          <div>
            <label style={labelStyle}>Provider</label>
            <select value={provider} onChange={e=>onProviderChange(e.target.value)} style={inputStyle}>
              {Object.entries(PROVIDER_DEFAULTS).map(([k,v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Model</label>
            <input value={model} onChange={e=>setModel(e.target.value)} placeholder={PROVIDER_DEFAULTS[provider]?.model || 'model id'} style={inputStyle} />
          </div>
        </div>

        {PROVIDER_DEFAULTS[provider]?.custom && (
          <div style={{ marginBottom:12 }}>
            <label style={labelStyle}>Base URL (OpenAI-compatible)</label>
            <input value={baseUrl} onChange={e=>setBaseUrl(e.target.value)} placeholder="https://your-host/v1" style={inputStyle} />
          </div>
        )}

        <div style={{ marginBottom:12 }}>
          <label style={labelStyle}>API Key {keyConfigured && <span style={{ color:'#3fb950' }}>(a key is saved — leave blank to keep it)</span>}</label>
          <input
            type="password"
            value={apiKey}
            onChange={e=>setApiKey(e.target.value)}
            autoComplete="off"
            placeholder={keyConfigured ? '•••••••••• (unchanged)' : 'paste your provider API key'}
            style={inputStyle}
          />
        </div>

        <div style={{ display:'flex', gap:10, alignItems:'center' }}>
          <button onClick={onSave} disabled={saving} style={{ padding:'8px 16px', background:'#238636', border:'none', borderRadius:6, color:'#fff', fontSize:13, fontWeight:600, cursor:saving?'default':'pointer', opacity:saving?0.6:1 }}>
            {saving ? 'Saving…' : 'Save'}
          </button>
          <button onClick={onTest} disabled={testing || !keyConfigured} title={keyConfigured?'':'Save a key first'} style={{ padding:'8px 16px', background:'#21262d', border:'1px solid #30363d', borderRadius:6, color:'#e6edf3', fontSize:13, cursor:(testing||!keyConfigured)?'default':'pointer', opacity:(testing||!keyConfigured)?0.6:1 }}>
            {testing ? 'Testing…' : 'Test connection'}
          </button>
          {savedMsg && <span style={{ fontSize:12, color:savedMsg.startsWith('Save failed')?'#f85149':'#3fb950' }}>{savedMsg}</span>}
        </div>

        {testResult && (
          <div style={{ marginTop:12, padding:'8px 12px', borderRadius:6, fontSize:12, background:testResult.ok?'#1a3a1a':'#2d1b1b', color:testResult.ok?'#3fb950':'#f85149' }}>
            {testResult.ok
              ? <>✓ Connected to <strong>{testResult.model}</strong> in {testResult.latency_ms} ms</>
              : <>✗ {testResult.error}</>}
          </div>
        )}
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

      {/* CRE-47 — AI Builder run history */}
      <RunHistory onRerun={handleRerun} />
      <AIBuilderPanel
        open={aiOpen}
        autoRunPrompt={rerunPrompt}
        onClose={() => { setAiOpen(false); setRerunPrompt(null) }}
      />
    </div>
  )
}
