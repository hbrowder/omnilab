import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAgentRuns } from '../../utils/api'

// CRE-47 (AILB-7) — AI Builder run history.
//
// Lists the last 10 build runs from GET /api/agent/runs (newest first) with
// prompt, status, lab_id and timestamps. Two actions per row:
//   • Re-run    — re-submit the prompt (opens the AI Builder pre-filled & runs)
//   • View lab  — navigate to /lab/{lab_id} (only when a lab survives the run)
//
// "Re-run" is delegated to the parent via onRerun(prompt) so the actual build
// happens through the existing AIBuilderPanel stream path.

const STATUS_STYLE = {
  running:   { bg: '#0d2847', border: '#1f6feb55', color: '#58a6ff', label: 'Running' },
  completed: { bg: '#0f2417', border: '#2ea04344', color: '#3fb950', label: 'Completed' },
  error:     { bg: '#2d1213', border: '#f8514944', color: '#f85149', label: 'Error' },
  cancelled: { bg: '#1c1206', border: '#9e6a0344', color: '#d29922', label: 'Cancelled' },
}

function fmtTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleString()
}

function StatusPill({ status }) {
  const s = STATUS_STYLE[status] || { bg: '#21262d', border: '#30363d', color: '#8b949e', label: status || 'unknown' }
  return (
    <span style={{ fontSize: 11, padding: '2px 10px', borderRadius: 12, background: s.bg,
      border: `1px solid ${s.border}`, color: s.color, whiteSpace: 'nowrap' }}>
      {s.label}
    </span>
  )
}

export default function RunHistory({ onRerun }) {
  const navigate = useNavigate()
  const [runs, setRuns] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    getAgentRuns()
      .then((r) => { setRuns(r?.data?.data?.runs || []); setError(null) })
      .catch(() => setError('Could not load run history.'))
  }

  useEffect(() => { load() }, [])

  return (
    <div style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 10, padding: 16, marginTop: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3', flex: 1 }}>
          ✨ AI Builder — Recent Runs
        </div>
        <button onClick={load}
          style={{ background: '#21262d', border: '1px solid #30363d', borderRadius: 6,
            color: '#adbac7', cursor: 'pointer', fontSize: 12, padding: '4px 10px' }}>
          ↻ Refresh
        </button>
      </div>

      {error && (
        <div style={{ fontSize: 12, color: '#f85149' }}>{error}</div>
      )}

      {!error && runs && runs.length === 0 && (
        <div style={{ fontSize: 13, color: '#8b949e' }}>No builds yet. Use “Build with AI” to create one.</div>
      )}

      {!error && runs === null && (
        <div style={{ fontSize: 13, color: '#8b949e' }}>Loading…</div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {(runs || []).map((run) => (
          <div key={run.id} style={{ background: '#0d1117', border: '1px solid #21262d',
            borderRadius: 8, padding: '10px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: '#e6edf3', whiteSpace: 'nowrap',
                  overflow: 'hidden', textOverflow: 'ellipsis' }} title={run.prompt}>
                  {run.prompt || '(no prompt)'}
                </div>
                <div style={{ fontSize: 11, color: '#6e7681', marginTop: 3 }}>
                  {fmtTime(run.started_at)}
                  {run.tool_call_count ? ` · ${run.tool_call_count} tool calls` : ''}
                  {run.total_tokens ? ` · ${run.total_tokens} tokens` : ''}
                  {run.lab_id ? ` · lab ${String(run.lab_id).slice(0, 8)}` : ''}
                </div>
              </div>
              <StatusPill status={run.status} />
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button onClick={() => onRerun?.(run.prompt)}
                disabled={!run.prompt}
                style={{ background: '#21262d', border: '1px solid #30363d', borderRadius: 6,
                  color: run.prompt ? '#adbac7' : '#484f58', cursor: run.prompt ? 'pointer' : 'default',
                  fontSize: 12, padding: '4px 10px' }}>
                ↻ Re-run
              </button>
              {run.lab_id && (
                <button onClick={() => navigate('/lab/' + run.lab_id)}
                  style={{ background: '#21262d', border: '1px solid #30363d', borderRadius: 6,
                    color: '#58a6ff', cursor: 'pointer', fontSize: 12, padding: '4px 10px' }}>
                  → View lab
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
