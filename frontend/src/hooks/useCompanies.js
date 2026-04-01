import { useState, useEffect, useCallback } from 'react'
import { api } from '../lib/api'

export function useCompanies() {
  const [companies, setCompanies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const data = await api.companies.list()
      setCompanies(data)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const toggleIncluded = useCallback(async (id, currentIncluded) => {
    const newVal = currentIncluded ? 0 : 1
    // Optimistic update
    setCompanies(cs => cs.map(c => c.company_id === id ? { ...c, included: newVal } : c))
    try {
      await api.companies.update(id, { included: newVal })
    } catch {
      // Rollback
      setCompanies(cs => cs.map(c => c.company_id === id ? { ...c, included: currentIncluded } : c))
    }
  }, [])

  return { companies, loading, error, reload: load, toggleIncluded }
}

export function useCompany(id) {
  const [company, setCompany] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    if (!id) return
    try {
      setLoading(true)
      const data = await api.companies.get(id)
      setCompany(data)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  return { company, loading, error, reload: load, setCompany }
}
