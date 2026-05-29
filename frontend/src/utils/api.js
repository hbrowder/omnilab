import axios from 'axios'
// Same-origin relative base: prod serves the SPA from the backend (:5000) and
// dev proxies /api via Vite (:5173 -> :5000). A hard-coded host IP broke the
// moment the bind defaulted to 127.0.0.1 and on any other host. (CRE-45 follow-up)
const API_BASE = '/api'
const api = axios.create({ baseURL: API_BASE })
export { API_BASE }
export const getLabs = () => api.get('/labs/')
export const createLab = (data) => api.post('/labs/', data)
export const getLab = (id) => api.get('/labs/'+id)
export const exportLab = (id) => api.get('/labs/'+id+'/export')
export const importLab = (bundle) => api.post('/labs/import', bundle)
export const deleteLab = (id) => api.delete('/labs/'+id)
export const getTopology = (id) => api.get('/labs/'+id+'/topology')
export const addNode = (data) => api.post('/nodes/', data)
export const deleteNode = (id) => api.delete('/nodes/'+id)
export const updateNode = (id, x, y) => api.put('/nodes/'+id+'?x='+x+'&y='+y)
export const getTemplates = (category) => api.get('/templates/', { params: category ? { category } : {} })
export const getCategories = () => api.get('/templates/categories')
export const deployTemplate = (id, name) => api.post('/templates/'+id+'/deploy', null, { params: { lab_name: name } })
export const getHealth = () => api.get('/system/health')
export const getSystemInfo = () => api.get('/system/info')
export const updateNodeConfig = (id, data) => api.patch('/nodes/'+id, data)
export const updateNodeMeta = (id, data) => api.patch('/nodes/'+id, data)

// CRE-15 / CRE-16 — first-run wizard
export const getFirstRunStatus = () => api.get('/system/first-run')
export const completeFirstRun = (data) => api.post('/system/first-run/complete', data)

// CRE-39 — docker provisioning frontend integration
// Note: web-info lives at /api/labs/{lab_id}/nodes/{node_id}/web-info,
// NOT /api/nodes/{node_id}/web-info — the lab_id is in the URL so the
// proxy can validate ownership without an extra DB hop.
export const getNodeWebInfo = (labId, nodeId) =>
  api.get(`/labs/${labId}/nodes/${nodeId}/web-info`)

// Build a ws:// or wss:// URL relative to the current page origin. Works
// in dev (Vite proxy at :5173 -> backend :5000) and prod (same-origin).
export const provisionWsUrl = (nodeId) => {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/api/nodes/${nodeId}/provision-ws`
}

// CRE-45 / AILB-5 — BYO-key AI provider config.
// GET never returns the api_key (only api_key_set bool). POST is write-only for
// the key. /agent/test pings the configured provider.
export const getAIProvider = () => api.get('/settings/ai-provider')
export const saveAIProvider = (data) => api.post('/settings/ai-provider', data)
export const testAIProvider = () => api.post('/agent/test')

// CRE-64: Drawing Tools - Text Objects API
export const getTextObjects = (labId) => api.get(`/labs/${labId}/textobjects`)
export const createTextObject = (labId, data) => api.post(`/labs/${labId}/textobjects`, data)
export const updateTextObject = (labId, objId, data) => api.patch(`/labs/${labId}/textobjects/${objId}`, data)
export const deleteTextObject = (labId, objId) => api.delete(`/labs/${labId}/textobjects/${objId}`)

// CRE-46 — AI Lab Builder ("Build with AI").
//
// The build endpoint streams Server-Sent Events. Browser EventSource is
// GET-only and cannot send a JSON body, so we POST with fetch() and read the
// ReadableStream ourselves, parsing `data: {json}\n\n` frames as they arrive.
//
// Backend (CRE-44) emits one JSON object per frame with a `type`:
//   thinking     { type, text }
//   tool_call    { type, name, args }
//   tool_result  { type, name, ok, data? , error? }   error = {code,message,details}
//   done         { type, lab_id, summary }
//   error        { type, message }
//
// Usage:
//   const ctrl = new AbortController()
//   await streamAgentBuild({ prompt }, onEvent, ctrl.signal)
//   // ctrl.abort() to cancel.
export async function streamAgentBuild(body, onEvent, signal) {
  const resp = await fetch(`${API_BASE}/agent/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(body),
    signal,
  })
  if (!resp.ok || !resp.body) {
    throw new Error(`build request failed (HTTP ${resp.status})`)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  // Flush any complete `data:` frames currently in the buffer.
  const drain = () => {
    let idx
    // SSE frames are separated by a blank line (\n\n). A frame may contain
    // multiple `data:` lines which concatenate into one payload.
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const rawFrame = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      const dataLines = rawFrame
        .split('\n')
        .filter((l) => l.startsWith('data:'))
        .map((l) => l.slice(5).replace(/^ /, ''))
      if (dataLines.length === 0) continue
      const payload = dataLines.join('\n').trim()
      if (!payload) continue
      try {
        onEvent(JSON.parse(payload))
      } catch {
        // Ignore unparseable frames rather than aborting the whole stream.
      }
    }
  }

  // Normalize CRLF so frame splitting on \n\n is reliable.
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
    drain()
  }
  buffer += decoder.decode().replace(/\r\n/g, '\n')
  // Make sure a trailing frame without a closing blank line still parses.
  if (buffer.trim()) buffer += '\n\n'
  drain()
}

// CRE-47 — AI Lab Builder run history + cancel.
//
// cancelAgentBuild signals the backend to gracefully stop an in-flight build
// (it polls the flag between tool calls). getAgentRuns returns the last 10 runs
// for the history UI. Both use the shared axios client (not the SSE fetch path).
export const cancelAgentBuild = (runId) => api.post(`/agent/build/${runId}/cancel`)
export const getAgentRuns = () => api.get('/agent/runs')

export default api
