import axios from 'axios'
const api = axios.create({ baseURL: '/api' })
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

// CRE-64: Drawing Tools - Text Objects API
export const getTextObjects = (labId) => api.get(`/labs/${labId}/textobjects`)
export const createTextObject = (labId, data) => api.post(`/labs/${labId}/textobjects`, data)
export const updateTextObject = (labId, objId, data) => api.patch(`/labs/${labId}/textobjects/${objId}`, data)
export const deleteTextObject = (labId, objId) => api.delete(`/labs/${labId}/textobjects/${objId}`)

export default api
