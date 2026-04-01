import { useState, useEffect, useCallback } from 'react'
import { api } from '../lib/api'

export function useFlows() {
  const [flows, setFlows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setFlows(await api.flows.list())
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])
  return { flows, loading, error, reload: load, setFlows }
}

export function useFlow(id) {
  const [flow, setFlow] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    api.flows.get(id).then(setFlow).finally(() => setLoading(false))
  }, [id])

  return { flow, loading, setFlow }
}
