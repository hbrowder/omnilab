import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../../store'
import { streamAgentBuild, cancelAgentBuild } from '../../utils/api'

// CRE-46 (AILB-6) — "Build with AI" panel.
//
// Chat-style prompt input + example prompts. On submit we POST to
// /api/agent/build and consume the SSE stream (via fetch + ReadableStream,
// see utils/api.js streamAgentBuild). Each event renders as an activity-log
// card. On `done` we navigate to /lab/{lab_id}; on `error` we surface a toast
// with a retry affordance.
//
// State lives in the shared Zustand store (aiBuild slice) so the panel can be
// closed/reopened mid-build without losing the log.

const EXAMPLE_PROMPTS = [
  { label: 'OSPF area 0/1 lab', text: 'Build an OSPF lab with two areas (area 0 and area 1) connected by an ABR. Use FRRouting nodes and add startup configs that bring up OSPF on the right interfaces.' },
  { label: '3-tier campus with BGP', text: 'Build a 3-tier campus network (core, distribution, access) using routers, with BGP peering between the core routers and a couple of host endpoints.' },
  { label: 'K8s + Wazuh SIEM', text: 'Build a lab with a small Kubernetes cluster and a Wazuh SIEM node so I can practice monitoring container workloads.' },
]

// ── tiny presentational helpers ──────────────────────────────────────────

// Friendly one-liner for a tool_call card.
function describeToolCall(name, args = {}) {
  switch (name) {
    case 'create_lab':
      return `Creating lab: ${args.name || '(unnamed)'}`
    case 'create_node':
      return `Creating node: ${args.name || '?'}${args.image ? ` (${args.image})` : ''}`
    case 'create_link': {
      const a = args.a?.node_id ? `${args.a.node_id}${args.a.iface ? ':' + args.a.iface : ''}` : '?'
      const b = args.b?.node_id ? `${args.b.node_id}${args.b.iface ? ':' + args.b.iface : ''}` : '?'
      return `Linking ${a} ↔ ${b}`
    }
    case 'set_config':
      return `Applying config to ${args.node_id || 'node'}${args.mode ? ` (${args.mode})` : ''}`
    case 'list_inventory':
      return 'Checking available images & capacity'
    case 'lab_state':
      return 'Reviewing the lab so far'
    case 'start_node':
      return `Starting node ${args.node_id || ''}`
    case 'stop_node':
      return `Stopping node ${args.node_id || ''}`
    default:
      return name ? `${name}` : 'Tool call'
  }
}

const TOOL_ICON = {
  create_lab: '🧪', create_node: '🔧', create_link: '🔗', set_config: '📝',
  list_inventory: '📦', lab_state: '🔍', start_node: '▶️', stop_node: '⏹️',
}

// A single thinking event — collapsible reasoning. Shows a one-line preview of
// the reasoning when collapsed so the user gets context without expanding, and
// defaults to collapsed to keep the log scannable.
function ThinkingCard({ text }) {
  const [open, setOpen] = useState(false)
  const preview = (text || '').replace(/\s+/g, ' ').trim()
  const short = preview.length > 80 ? preview.slice(0, 80) + '…' : preview
  return (
    <div style={{ background: '#0d1117', border: '1px solid #21262d', borderRadius: 8, padding: '8px 12px' }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer',
          fontSize: 12, padding: 0, display: 'flex', alignItems: 'center', gap: 6, width: '100%', textAlign: 'left' }}>
        <span>{open ? '▾' : '▸'}</span>
        <span style={{ whiteSpace: 'nowrap' }}>💭 Reasoning</span>
        {!open && short && (
          <span style={{ color: '#6e7681', overflow: 'hidden', textOverflow: 'ellipsis',
            whiteSpace: 'nowrap', flex: 1, minWidth: 0 }}>— {short}</span>
        )}
      </button>
      {open && (
        <div style={{ marginTop: 6, fontSize: 12, color: '#adbac7', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
          {text}
        </div>
      )}
    </div>
  )
}

// A tool_call card paired (in render) with its tool_result status.
function ToolCard({ name, args, result }) {
  const icon = TOOL_ICON[name] || '⚙️'
  const ok = result?.ok
  const pending = result === undefined
  const errMsg = result?.error?.message || result?.error?.code
  return (
    <div style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 8,
      padding: '10px 12px', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
      <span style={{ fontSize: 15, lineHeight: '20px' }}>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, color: '#e6edf3' }}>{describeToolCall(name, args)}</div>
        {!ok && errMsg && (
          <div style={{ fontSize: 11, color: '#f85149', marginTop: 3 }}>{errMsg}</div>
        )}
      </div>
      <span style={{ fontSize: 14, lineHeight: '20px' }}>
        {pending ? (
          <span style={{ color: '#8b949e' }}>⏳</span>
        ) : ok ? (
          <span style={{ color: '#3fb950' }}>✓</span>
        ) : (
          <span style={{ color: '#f85149' }}>✗</span>
        )}
      </span>
    </div>
  )
}

// Combine the flat event list into renderable rows. tool_result events attach
// to their preceding tool_call (matched on name, in order).
function buildRows(events) {
  const rows = []
  const pendingByName = {} // name -> index in rows of an unresolved tool_call
  for (const ev of events) {
    if (ev.type === 'thinking') {
      rows.push({ kind: 'thinking', text: ev.text })
    } else if (ev.type === 'tool_call') {
      rows.push({ kind: 'tool', name: ev.name, args: ev.args, result: undefined })
      pendingByName[ev.name] = rows.length - 1
    } else if (ev.type === 'tool_result') {
      const idx = pendingByName[ev.name]
      if (idx !== undefined && rows[idx] && rows[idx].result === undefined) {
        rows[idx].result = { ok: ev.ok, data: ev.data, error: ev.error }
        delete pendingByName[ev.name]
      } else {
        // Orphan result (no matching open call) — show it standalone.
        rows.push({ kind: 'tool', name: ev.name, args: {}, result: { ok: ev.ok, data: ev.data, error: ev.error } })
      }
    }
  }
  return rows
}

export default function AIBuilderPanel({ open, onClose, autoRunPrompt }) {
  const navigate = useNavigate()
  const {
    aiBuild, aiBuildStart, aiBuildSetRunId, aiBuildPushEvent, aiBuildDone,
    aiBuildError, aiBuildCancelled, aiBuildReset,
  } = useStore()

  const [input, setInput] = useState(aiBuild.prompt || '')
  const [cancelling, setCancelling] = useState(false)
  const abortRef = useRef(null)
  const logEndRef = useRef(null)

  const building = aiBuild.status === 'building'
  const rows = buildRows(aiBuild.events)

  // Auto-scroll the activity log to the newest card.
  useEffect(() => {
    if (logEndRef.current) logEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [aiBuild.events.length, aiBuild.status])

  // On `done`, give the user a beat to see the final card, then navigate.
  useEffect(() => {
    if (aiBuild.status === 'done' && aiBuild.labId) {
      const t = setTimeout(() => {
        onClose?.()
        navigate('/lab/' + aiBuild.labId)
      }, 900)
      return () => clearTimeout(t)
    }
  }, [aiBuild.status, aiBuild.labId, navigate, onClose])

  // Abort any in-flight stream if the component unmounts.
  useEffect(() => () => { abortRef.current?.abort() }, [])

  const runBuild = async (prompt) => {
    const trimmed = (prompt ?? input).trim()
    if (!trimmed || building) return
    setInput(trimmed)
    aiBuildStart(trimmed)

    const ctrl = new AbortController()
    abortRef.current = ctrl
    setCancelling(false)
    let sawTerminal = false
    try {
      await streamAgentBuild({ prompt: trimmed }, (ev) => {
        if (ev.type === 'run_started') {
          // CRE-47: capture the run_id so Stop can POST /cancel.
          aiBuildSetRunId(ev.run_id)
        } else if (ev.type === 'done') {
          sawTerminal = true
          aiBuildDone(ev.lab_id, ev.summary)
        } else if (ev.type === 'cancelled') {
          sawTerminal = true
          aiBuildCancelled()
        } else if (ev.type === 'error') {
          sawTerminal = true
          aiBuildError(ev.message || 'The builder reported an error.')
        } else {
          // thinking / tool_call / tool_result
          aiBuildPushEvent(ev)
        }
      }, ctrl.signal)
      // Stream closed without a terminal event — treat as an error so the
      // user isn't stuck on a spinner.
      if (!sawTerminal) {
        aiBuildError('The build stream ended unexpectedly. Please retry.')
      }
    } catch (e) {
      if (e?.name === 'AbortError') return // stream torn down locally
      aiBuildError(e?.message || 'Could not reach the AI builder. Is the backend running?')
    } finally {
      abortRef.current = null
      setCancelling(false)
    }
  }

  // Graceful cancel: ask the backend to stop the run (it tears down any partial
  // lab and emits a terminal `cancelled` event we render). We keep the SSE
  // stream open so that terminal event arrives; if it never does, the stream
  // close path handles it. Falls back to a local abort if we have no run_id yet.
  const cancel = async () => {
    const runId = aiBuild.runId
    if (!runId) {
      // No run_id known yet — just tear down locally and reset.
      abortRef.current?.abort()
      abortRef.current = null
      aiBuildReset()
      return
    }
    setCancelling(true)
    try {
      await cancelAgentBuild(runId)
      // Leave the stream open; the backend will emit `cancelled`.
    } catch {
      // Backend unreachable — fall back to a hard local stop.
      abortRef.current?.abort()
      abortRef.current = null
      aiBuildCancelled()
      setCancelling(false)
    }
  }

  const retry = () => {
    const prompt = aiBuild.prompt || input
    aiBuildReset()
    runBuild(prompt)
  }

  // CRE-47 re-run: when opened with an autoRunPrompt (from Run History), fill
  // the input and kick off the build once per distinct prompt value.
  const lastAutoRef = useRef(null)
  useEffect(() => {
    if (open && autoRunPrompt && autoRunPrompt !== lastAutoRef.current && !building) {
      lastAutoRef.current = autoRunPrompt
      setInput(autoRunPrompt)
      runBuild(autoRunPrompt)
    }
    if (!open) lastAutoRef.current = null
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, autoRunPrompt])

  if (!open) return null

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1000, display: 'flex', justifyContent: 'flex-end',
      background: 'rgba(1,4,9,0.55)' }} onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ width: 'min(460px, 100%)', height: '100%', background: '#010409',
          borderLeft: '1px solid #21262d', display: 'flex', flexDirection: 'column',
          fontFamily: 'system-ui, sans-serif', boxShadow: '-8px 0 24px rgba(0,0,0,0.4)' }}>

        {/* Header */}
        <div style={{ padding: '16px 18px', borderBottom: '1px solid #21262d',
          display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#e6edf3', flex: 1 }}>
            ✨ Build with AI
          </div>
          <button onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#8b949e',
              cursor: 'pointer', fontSize: 18, lineHeight: 1 }}>×</button>
        </div>

        {/* Prompt input */}
        <div style={{ padding: '14px 18px', borderBottom: '1px solid #161b22' }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); runBuild() }
            }}
            placeholder="Describe the lab you want to build…  (⌘/Ctrl + Enter to send)"
            disabled={building}
            rows={3}
            style={{ width: '100%', boxSizing: 'border-box', resize: 'vertical',
              background: '#0d1117', border: '1px solid #30363d', borderRadius: 8,
              color: '#e6edf3', fontSize: 13, padding: '10px 12px', fontFamily: 'inherit',
              outline: 'none', opacity: building ? 0.6 : 1 }}
          />
          <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            {!building ? (
              <button
                onClick={() => runBuild()}
                disabled={!input.trim()}
                style={{ flex: 1, background: input.trim() ? '#238636' : '#21262d',
                  border: '1px solid ' + (input.trim() ? '#2ea043' : '#30363d'),
                  borderRadius: 8, color: input.trim() ? '#fff' : '#8b949e', cursor: input.trim() ? 'pointer' : 'default',
                  fontSize: 13, fontWeight: 600, padding: '9px 14px' }}>
                Build lab
              </button>
            ) : (
              <button
                onClick={cancel}
                disabled={cancelling}
                style={{ flex: 1, background: cancelling ? '#5a1d1d' : '#da3633',
                  border: '1px solid ' + (cancelling ? '#7d2b2b' : '#f85149'),
                  borderRadius: 8, color: '#fff', cursor: cancelling ? 'default' : 'pointer',
                  fontSize: 14, fontWeight: 700, padding: '10px 14px',
                  opacity: cancelling ? 0.8 : 1 }}>
                {cancelling ? 'Stopping…' : '⏹ Stop'}
              </button>
            )}
          </div>

          {/* Example prompts */}
          {aiBuild.status === 'idle' && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11, color: '#8b949e', marginBottom: 6 }}>Try an example:</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {EXAMPLE_PROMPTS.map((ex) => (
                  <button key={ex.label}
                    onClick={() => setInput(ex.text)}
                    style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 14,
                      color: '#adbac7', cursor: 'pointer', fontSize: 11, padding: '5px 11px' }}
                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#58a6ff' }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#30363d' }}>
                    {ex.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Activity log */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '14px 18px' }}>
          {aiBuild.status === 'idle' && rows.length === 0 && (
            <div style={{ color: '#484f58', fontSize: 13, textAlign: 'center', marginTop: 30, lineHeight: 1.6 }}>
              Describe the network you want and the AI will assemble it node by node.
              <br />Each step streams in live below.
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {rows.map((row, i) =>
              row.kind === 'thinking'
                ? <ThinkingCard key={i} text={row.text} />
                : <ToolCard key={i} name={row.name} args={row.args} result={row.result} />
            )}

            {building && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#58a6ff', fontSize: 12,
                padding: '6px 2px' }}>
                <span className="ailb-pulse" style={{ width: 8, height: 8, borderRadius: '50%', background: '#58a6ff' }} />
                Thinking…
              </div>
            )}

            {aiBuild.status === 'done' && (
              <div style={{ background: '#0f2417', border: '1px solid #2ea04344', borderRadius: 8,
                padding: '12px 14px', color: '#3fb950', fontSize: 13 }}>
                ✓ Lab ready{aiBuild.summary ? ` — ${aiBuild.summary}` : ''}. Opening the canvas…
              </div>
            )}

            {aiBuild.status === 'cancelled' && (
              <div style={{ background: '#1c1206', border: '1px solid #9e6a0344', borderRadius: 8,
                padding: '12px 14px', color: '#d29922', fontSize: 13 }}>
                ⏹ Build cancelled. Any partially-built lab was cleaned up.
              </div>
            )}
          </div>

          <div ref={logEndRef} />
        </div>

        {/* Error toast / retry affordance */}
        {aiBuild.status === 'error' && (
          <div style={{ padding: '12px 18px', borderTop: '1px solid #21262d', background: '#160b0e' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <span style={{ fontSize: 16 }}>⚠️</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#f85149' }}>Build failed</div>
                <div style={{ fontSize: 12, color: '#d6a5a5', marginTop: 3, lineHeight: 1.5 }}>
                  {aiBuild.error}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
              <button onClick={retry}
                style={{ flex: 1, background: '#238636', border: '1px solid #2ea043', borderRadius: 8,
                  color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600, padding: '8px 14px' }}>
                ↻ Retry
              </button>
              <button onClick={aiBuildReset}
                style={{ background: '#21262d', border: '1px solid #30363d', borderRadius: 8,
                  color: '#adbac7', cursor: 'pointer', fontSize: 13, padding: '8px 14px' }}>
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Cancelled — offer to build again or dismiss */}
        {aiBuild.status === 'cancelled' && (
          <div style={{ padding: '12px 18px', borderTop: '1px solid #21262d', background: '#161106' }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={retry}
                style={{ flex: 1, background: '#238636', border: '1px solid #2ea043', borderRadius: 8,
                  color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600, padding: '8px 14px' }}>
                ↻ Build again
              </button>
              <button onClick={aiBuildReset}
                style={{ background: '#21262d', border: '1px solid #30363d', borderRadius: 8,
                  color: '#adbac7', cursor: 'pointer', fontSize: 13, padding: '8px 14px' }}>
                Dismiss
              </button>
            </div>
          </div>
        )}

        <style>{`
          @keyframes ailbPulse { 0%,100% { opacity: 1 } 50% { opacity: 0.25 } }
          .ailb-pulse { animation: ailbPulse 1s ease-in-out infinite; }
        `}</style>
      </div>
    </div>
  )
}
