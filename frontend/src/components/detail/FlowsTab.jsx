import { useState, useEffect } from 'react'
import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { StatusBadge } from '../shared/Badge'
import ConfirmPopover from '../shared/ConfirmPopover'
import { api } from '../../lib/api'

const STATUS_CYCLE = ['candidate', 'confirmed', 'rejected']

export default function FlowsTab({ companyId, refresh }) {
  const { colors } = useTheme()
  const [flows, setFlows] = useState([])
  const [loading, setLoading] = useState(true)
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [editingNotes, setEditingNotes] = useState(null)
  const [notesVal, setNotesVal] = useState('')

  const load = () => {
    setLoading(true)
    api.companies.flows(companyId)
      .then(setFlows)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [companyId, refresh])

  const cycleStatus = async (flow) => {
    const idx = STATUS_CYCLE.indexOf(flow.status)
    const next = STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length]
    setFlows(fs => fs.map(f => f.flow_id === flow.flow_id ? { ...f, status: next } : f))
    await api.flows.update(flow.flow_id, { status: next })
  }

  const saveNotes = async (flow) => {
    setFlows(fs => fs.map(f => f.flow_id === flow.flow_id ? { ...f, notes: notesVal } : f))
    setEditingNotes(null)
    await api.flows.update(flow.flow_id, { notes: notesVal })
  }

  const deleteFlow = async (flowId) => {
    setConfirmDelete(null)
    setFlows(fs => fs.filter(f => f.flow_id !== flowId))
    await api.flows.delete(flowId)
  }

  if (loading) return <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>Loading…</div>
  if (flows.length === 0) return (
    <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>
      No flows for this company yet. Use "Create Flow" in the Streams tab.
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {flows.map(flow => {
        const isFrom = flow.from_company_id === companyId
        return (
          <div key={flow.flow_id} style={{
            background: colors.card, border: `1px solid ${colors.border}`,
            borderRadius: '6px', padding: '10px 12px',
          }}>
            {/* Flow header row */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim }}>{flow.flow_id}</span>
              <button
                onClick={() => cycleStatus(flow)}
                title="Click to cycle status"
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
              >
                <StatusBadge status={flow.status} />
              </button>
              {flow.flow_type && (
                <span style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim }}>
                  [{flow.flow_type}]
                </span>
              )}
              {flow.flow_kton_per_year != null && (
                <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textSecondary, marginLeft: 'auto' }}>
                  {flow.flow_kton_per_year.toFixed(3)} kt/yr
                </span>
              )}
            </div>

            {/* From → To */}
            <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.textSecondary, marginBottom: '6px' }}>
              <span style={{ color: isFrom ? colors.accent : colors.textDim }}>{flow.from_company_name}</span>
              {flow.from_stream_name && <span style={{ color: colors.textDim }}> / {flow.from_stream_name}</span>}
              <span style={{ color: colors.textDim }}> → </span>
              <span style={{ color: !isFrom ? colors.accent : colors.textDim }}>{flow.to_company_name}</span>
              {flow.to_stream_name && <span style={{ color: colors.textDim }}> / {flow.to_stream_name}</span>}
            </div>

            {/* Notes row */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {editingNotes === flow.flow_id ? (
                <>
                  <input
                    autoFocus
                    value={notesVal}
                    onChange={e => setNotesVal(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') saveNotes(flow); if (e.key === 'Escape') setEditingNotes(null) }}
                    style={{
                      flex: 1, fontFamily: FONT, fontSize: '11px',
                      background: colors.hover, border: `1px solid ${colors.accent}`,
                      color: colors.textPrimary, borderRadius: '3px', padding: '3px 6px',
                    }}
                  />
                  <button onClick={() => saveNotes(flow)} style={{ fontFamily: FONT, fontSize: '10px', color: colors.scoreHigh, background: 'none', border: 'none', cursor: 'pointer' }}>Save</button>
                  <button onClick={() => setEditingNotes(null)} style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, background: 'none', border: 'none', cursor: 'pointer' }}>Cancel</button>
                </>
              ) : (
                <span
                  onClick={() => { setEditingNotes(flow.flow_id); setNotesVal(flow.notes || '') }}
                  style={{
                    flex: 1, fontFamily: FONT, fontSize: '11px',
                    color: flow.notes ? colors.textSecondary : colors.textDim,
                    cursor: 'text', padding: '3px 0',
                  }}
                >
                  {flow.notes || 'Add notes…'}
                </span>
              )}

              {/* Delete */}
              <div style={{ position: 'relative', flexShrink: 0 }}>
                <button
                  onClick={() => setConfirmDelete(confirmDelete === flow.flow_id ? null : flow.flow_id)}
                  style={{
                    fontFamily: FONT, fontSize: '10px', padding: '2px 7px',
                    background: 'transparent', border: `1px solid ${colors.border}`,
                    color: colors.textDim, borderRadius: '3px', cursor: 'pointer',
                  }}
                >
                  Delete
                </button>
                {confirmDelete === flow.flow_id && (
                  <ConfirmPopover
                    message={`Delete flow ${flow.flow_id}?`}
                    onConfirm={() => deleteFlow(flow.flow_id)}
                    onCancel={() => setConfirmDelete(null)}
                  />
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
