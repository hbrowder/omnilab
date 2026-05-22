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

export default api
