import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  getBezierPath,
  BaseEdge,
  EdgeLabelRenderer,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { FONT, STATUS_COLORS } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { useGraph } from '../../hooks/useGraph'
import CompanyNode from './CompanyNode'
import { ConnectingContext } from './ConnectingContext'
import CreateFlowModal from '../detail/CreateFlowModal'

const nodeTypes = { company: CompanyNode }

// Custom flow edge with midpoint dot + label
function FlowEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data, style }) {
  const { colors } = useTheme()
  const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition })
  const status = data?.status || 'candidate'
  const color = STATUS_COLORS[status] || colors.textDim

  const effectiveStyle = {
    ...style,
    strokeWidth: data?.isHovered ? (style?.strokeWidth ?? 1.5) * 2.5 : style?.strokeWidth,
    opacity: data?.anyHovered && !data?.isHovered ? 0.15 : 1,
    filter: data?.isHovered ? `drop-shadow(0 0 5px ${color})` : undefined,
    transition: 'opacity 0.15s',
  }

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={effectiveStyle} />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: 'all',
            cursor: 'pointer',
          }}
        >
          <div style={{
            width: '8px', height: '8px', borderRadius: '50%',
            background: color, border: `2px solid ${colors.card}`,
            boxShadow: `0 0 4px ${color}88`,
            margin: '0 auto',
            opacity: data?.anyHovered && !data?.isHovered ? 0.15 : 1,
            transition: 'opacity 0.15s',
          }} />
          {data?.label && (
            <div style={{
              marginTop: '2px',
              fontFamily: FONT, fontSize: '9px', color: colors.textDim,
              background: colors.card, padding: '1px 4px', borderRadius: '3px',
              border: `1px solid ${colors.border}`,
              whiteSpace: 'nowrap', textAlign: 'center',
              opacity: data?.anyHovered && !data?.isHovered ? 0.15 : 1,
              transition: 'opacity 0.15s',
            }}>
              {data.label}
            </div>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  )
}

const edgeTypes = { flow: FlowEdge }

const EXTERNAL_TYPES = ['import_source', 'export_sink', 'waste_facility']
const genericDir = (nodeType) => nodeType === 'import_source' ? 'output' : 'input'

function makeNode(n, selectedId) {
  return {
    id: n.id,
    type: 'company',
    position: { x: n.x ?? 0, y: n.y ?? 0 },
    data: {
      label: n.label,
      company_id: n.id,
      node_type: n.node_type,
      sector: n.sector,
      streams: n.streams || [],
    },
    selected: n.id === selectedId,
  }
}

function applyStatus(edge, status) {
  const color = STATUS_COLORS[status] || '#9aa0ad'
  return {
    ...edge,
    style: {
      stroke: color,
      strokeWidth: status === 'confirmed' ? 2.5 : 1.5,
      strokeDasharray: status === 'candidate' ? '6 3' : status === 'rejected' ? '2 4' : undefined,
    },
    data: { ...edge.data, status },
  }
}

function buildEdges(graphData) {
  return (graphData?.edges || []).map(e => {
    const label = e.flow_kton_per_year != null ? `${e.flow_kton_per_year.toFixed(1)} kt/yr` : null
    return applyStatus({
      id: e.id,
      type: 'flow',
      source: e.from_company_id,
      target: e.to_company_id,
      sourceHandle: e.from_stream_id,
      targetHandle: e.to_stream_id,
      data: { flow_id: e.id, status: e.status || 'candidate', label },
    }, e.status || 'candidate')
  })
}

export default function ClusterGraph() {
  const { colors } = useTheme()
  const navigate = useNavigate()
  const params = useParams()
  const selectedId = params['*']?.split('/')[0] || null

  const { graphData, loading, savePositions } = useGraph()

  useEffect(() => {
    const onDeleted = (ev) =>
      setEdges(prev => prev.filter(e => e.id !== ev.detail.flowId))
    const onStatusChanged = (ev) =>
      setEdges(prev => prev.map(e => e.id === ev.detail.flowId ? applyStatus(e, ev.detail.status) : e))
    const onCreated = (ev) => {
      const f = ev.detail.flow
      const label = f.flow_kton_per_year != null ? `${f.flow_kton_per_year.toFixed(1)} kt/yr` : null
      const newEdge = applyStatus({
        id: f.flow_id,
        type: 'flow',
        source: f.from_company_id,
        target: f.to_company_id,
        sourceHandle: f.from_stream_id,
        targetHandle: f.to_stream_id,
        data: { flow_id: f.flow_id, status: f.status, label },
      }, f.status)
      setEdges(prev => [...prev, newEdge])
    }
    window.addEventListener('flow-deleted', onDeleted)
    window.addEventListener('flow-status-changed', onStatusChanged)
    window.addEventListener('flow-created', onCreated)
    return () => {
      window.removeEventListener('flow-deleted', onDeleted)
      window.removeEventListener('flow-status-changed', onStatusChanged)
      window.removeEventListener('flow-created', onCreated)
    }
  }, [])
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const posCache = useRef({})
  const initDone = useRef(false)

  // Drag-to-connect state
  const [connecting, setConnecting] = useState(null)
  const [flowModal, setFlowModal] = useState(null)

  // Edge hover highlight
  const [hoveredEdgeId, setHoveredEdgeId] = useState(null)
  const onEdgeMouseEnter = useCallback((_ev, edge) => setHoveredEdgeId(edge.id), [])
  const onEdgeMouseLeave = useCallback(() => setHoveredEdgeId(null), [])

  const displayEdges = useMemo(() => {
    if (!hoveredEdgeId) return edges
    return edges.map(e => ({
      ...e,
      data: { ...e.data, isHovered: e.id === hoveredEdgeId, anyHovered: true },
    }))
  }, [edges, hoveredEdgeId])

  // Initialize/rebuild nodes + edges when data arrives
  useEffect(() => {
    if (!graphData) return

    graphData.nodes.forEach(n => {
      if (n.x != null) posCache.current[n.id] = { x: n.x, y: n.y }
    })

    const unpositioned = graphData.nodes.filter(n => !(n.id in posCache.current))

    if (unpositioned.length > 0 && !initDone.current) {
      initDone.current = true
      const existing = Object.values(posCache.current)
      const maxX = existing.length > 0 ? Math.max(...existing.map(p => p.x)) + 300 : 60
      const cols = Math.ceil(Math.sqrt(unpositioned.length))

      unpositioned.forEach((n, i) => {
        posCache.current[n.id] = {
          x: maxX + (i % cols) * 300,
          y: Math.floor(i / cols) * 240 + 60,
        }
      })
      savePositions(Object.fromEntries(unpositioned.map(n => [n.id, posCache.current[n.id]])))
    }

    const enriched = graphData.nodes.map(n => ({
      ...n,
      x: posCache.current[n.id]?.x ?? n.x ?? 0,
      y: posCache.current[n.id]?.y ?? n.y ?? 0,
    }))
    setNodes(enriched.map(n => makeNode(n, selectedId)))
    setEdges(buildEdges(graphData))
  }, [graphData])

  // Update selection highlight without re-fetching
  useEffect(() => {
    setNodes(prev => prev.map(n => ({ ...n, selected: n.id === selectedId })))
  }, [selectedId])

  const onNodeDragStop = useCallback((_event, node) => {
    posCache.current[node.id] = { x: node.position.x, y: node.position.y }
    savePositions({ [node.id]: { x: node.position.x, y: node.position.y } })
  }, [savePositions])

  const onNodeClick = useCallback((_event, node) => {
    navigate(`/companies/${node.id}`)
  }, [navigate])

  const onEdgeClick = useCallback((_event, edge) => {
    if (edge.data?.flow_id) navigate(`/flows/${edge.data.flow_id}`)
  }, [navigate])

  // Build stream_id → { companyId, direction, streamName, nodeType } lookup for connection validation
  // Also registers generic-{companyId} handles for external nodes
  const streamMeta = useMemo(() => {
    const map = {}
    if (!graphData) return map
    graphData.nodes.forEach(n => {
      ;(n.streams || []).forEach(s => {
        map[s.stream_id] = { companyId: n.id, direction: s.direction, streamName: s.stream_name, nodeType: n.node_type }
      })
      if (EXTERNAL_TYPES.includes(n.node_type)) {
        const dir = genericDir(n.node_type)
        map[`generic-${n.id}`] = { companyId: n.id, direction: dir, streamName: null, nodeType: n.node_type, isGeneric: true }
      }
    })
    return map
  }, [graphData])

  const onConnectStart = useCallback((_event, { handleId }) => {
    if (!handleId) return
    const meta = streamMeta[handleId]
    if (!meta) return
    setConnecting({
      sourceStreamId: handleId,
      sourceCompanyId: meta.companyId,
      sourceDirection: meta.direction,
    })
  }, [streamMeta])

  const onConnectEnd = useCallback(() => {
    setConnecting(null)
  }, [])

  const isValidConnection = useCallback((connection) => {
    const src = streamMeta[connection.sourceHandle]
    const tgt = streamMeta[connection.targetHandle]
    if (!src || !tgt) return false
    if (src.companyId === tgt.companyId) return false
    if (src.direction === tgt.direction) return false
    return true
  }, [streamMeta])

  const onConnect = useCallback((connection) => {
    setConnecting(null)
    const srcMeta = streamMeta[connection.sourceHandle]
    const tgtMeta = streamMeta[connection.targetHandle]
    if (!srcMeta || !tgtMeta) return

    // Determine which side is output (from) and which is input (to)
    const srcIsOutput = srcMeta.direction === 'output'
    const outHandle = srcIsOutput ? connection.sourceHandle : connection.targetHandle
    const inHandle  = srcIsOutput ? connection.targetHandle : connection.sourceHandle
    const outMeta   = srcIsOutput ? srcMeta : tgtMeta
    const inMeta    = srcIsOutput ? tgtMeta : srcMeta

    setFlowModal({
      fromStreamId:   outMeta.isGeneric ? null : outHandle,
      fromCompanyId:  outMeta.companyId,
      fromStreamName: outMeta.streamName,
      fromNodeType:   outMeta.nodeType,
      toStreamId:     inMeta.isGeneric ? null : inHandle,
      toCompanyId:    inMeta.companyId,
      toStreamName:   inMeta.streamName,
      toNodeType:     inMeta.nodeType,
    })
  }, [streamMeta])

  const proOptions = useMemo(() => ({ hideAttribution: true }), [])

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>
        Loading graph…
      </div>
    )
  }

  return (
    <ConnectingContext.Provider value={connecting}>
      <div style={{ width: '100%', height: '100%' }}>
        <ReactFlow
          nodes={nodes}
          edges={displayEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeDragStop={onNodeDragStop}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onEdgeMouseEnter={onEdgeMouseEnter}
          onEdgeMouseLeave={onEdgeMouseLeave}
          onConnectStart={onConnectStart}
          onConnectEnd={onConnectEnd}
          onConnect={onConnect}
          isValidConnection={isValidConnection}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          nodesDraggable
          fitView
          fitViewOptions={{ padding: 0.15 }}
          proOptions={proOptions}
          style={{ background: colors.bg }}
        >
          <Background color={colors.border} gap={24} size={1} />
          <Controls
            style={{
              background: colors.card,
              border: `1px solid ${colors.border}`,
              borderRadius: '6px',
            }}
          />
        </ReactFlow>
      </div>

      {flowModal && (
        <CreateFlowModal
          prefill={flowModal}
          onClose={() => setFlowModal(null)}
          onCreated={() => setFlowModal(null)}
        />
      )}
    </ConnectingContext.Provider>
  )
}
