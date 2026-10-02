import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export default api

export const auth = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
}

export const applications = {
  list: (status?: string) =>
    api.get('/applications', { params: status ? { status } : {} }),
  create: (data: { applicant_name: string; loan_type: string; loan_amount: number }) =>
    api.post('/applications', data),
  get: (id: string) => api.get(`/applications/${id}`),
  dashboard: (id: string) => api.get(`/applications/${id}/dashboard`),
  riskScore: (id: string) => api.get(`/applications/${id}/risk-score`),
  consensus: (id: string) => api.get(`/applications/${id}/consensus`),
  review: (id: string, data: { decision: string; notes?: string }) =>
    api.post(`/applications/${id}/review`, data),
}

export const documents = {
  upload: (appId: string, file: File, hintType?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (hintType) form.append('hint_type', hintType)
    return api.post(`/applications/${appId}/documents`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  analyze: (docId: string) => api.post(`/documents/${docId}/analyze`),
}

export const auditLog = {
  list: (appId?: string) =>
    api.get('/audit-logs', { params: appId ? { application_id: appId } : {} }),
  verify: () => api.get('/audit-logs/verify'),
}
