const BASE = '/api'

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body !== undefined) opts.body = JSON.stringify(body)
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  if (res.status === 204) return null
  return res.json()
}

const get = (path) => request('GET', path)
const post = (path, body) => request('POST', path, body)
const patch = (path, body) => request('PATCH', path, body)
const del = (path) => request('DELETE', path)

// Companies
export const api = {
  companies: {
    list: () => get('/companies'),
    get: (id) => get(`/companies/${id}`),
    update: (id, body) => patch(`/companies/${id}`, body),
    streams: (id) => get(`/companies/${id}/streams`),
    flows: (id) => get(`/companies/${id}/flows`),
    createFlow: (id, body) => post(`/companies/${id}/flows`, body),
    normalization: {
      candidates: (id) => get(`/companies/${id}/normalization`),
      set: (id, streamId) => post(`/companies/${id}/normalization/set`, { stream_id: streamId }),
      clear: (id) => post(`/companies/${id}/normalization/clear`),
      setSetpoint: (id, setpoint) => post(`/companies/${id}/normalization/setpoint`, { setpoint }),
      setCustomFactor: (id, value) => post(`/companies/${id}/normalization/custom-factor`, { value }),
      clearCustomFactor: (id) => del(`/companies/${id}/normalization/custom-factor`),
    },
  },
  flows: {
    list: () => get('/flows'),
    get: (id) => get(`/flows/${id}`),
    update: (id, body) => patch(`/flows/${id}`, body),
    delete: (id) => del(`/flows/${id}`),
  },
  streams: {
    list: () => get('/streams'),
    get: (id) => get(`/streams/${id}`),
  },
  components: {
    list: () => get('/components'),
    get: (id) => get(`/components/${id}`),
    update: (id, body) => patch(`/components/${id}`, body),
  },
  carbon: {
    status: () => get('/carbon/status'),
    recalculate: () => post('/carbon/recalculate'),
    gaps: () => get('/carbon/gaps'),
  },
  graph: {
    get: () => get('/graph'),
    savePositions: (positions) => patch('/graph/positions', { positions }),
  },
  normalization: {
    recalculate: () => post('/normalization/recalculate'),
  },
}
