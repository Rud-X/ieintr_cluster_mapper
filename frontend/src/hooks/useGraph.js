import { useState, useEffect, useCallback } from 'react'
import { api } from '../lib/api'

function gridLayout(nodes) {
  const cols = Math.ceil(Math.sqrt(nodes.length))
  const spacing = 260
  return nodes.map((n, i) => ({
    ...n,
    position: { x: (i % cols) * spacing + 60, y: Math.floor(i / cols) * 200 + 60 },
  }))
}

export function useGraph() {
  const [graphData, setGraphData] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.graph.get()
      setGraphData(data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const savePositions = useCallback(async (positions) => {
    await api.graph.savePositions(positions)
  }, [])

  const buildInitialPositions = useCallback(async (nodes) => {
    const positioned = gridLayout(nodes)
    const posMap = {}
    positioned.forEach(n => { posMap[n.id] = { x: n.position.x, y: n.position.y } })
    await api.graph.savePositions(posMap)
    return posMap
  }, [])

  return { graphData, loading, reload: load, savePositions, buildInitialPositions }
}
