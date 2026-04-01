import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { StatusBadge } from '../shared/Badge'
import ConfirmPopover from '../shared/ConfirmPopover'
import { useFlow } from '../../hooks/useFlows'
import { api } from '../../lib/api'

const STATUS_CYCLE = ['candidate', 'confirmed', 'rejected']

function Field({ label, value, dim }) {
  const { colors } = useTheme()
  return (
    <div style={{ marginBottom: '10px' }}>
      <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '2px' }}>{label}</div>
      <div style={{ fontFamily: FONT, fontSize: '12px', color: dim ? colors.textSecondary : colors.textPrimary }}>
        {value ?? '—'}
      </div>
    </div>
  )
}

export default function FlowDetail() {
  const { colors } = useTheme()
  const { id } = useParams()
  const navigate = useNavigate()
  const { flow, loading, setFlow } = useFlow(id)
  const [editingNotes, setEditingNotes] = useState(false)
  const [notesVal, setNotesVal] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)

  const cycleStatus = async () => {
    const idx = STATUS_CYCLE.indexOf(flow.status)
    const next = STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length]
    setFlow(f => ({ ...f, status: next }))
    await api.flows.update(id, { status: next })
    window.dispatchEvent(new CustomEvent('flow-status-changed', { detail: { flowId: id, status: next } }))
  }

  const saveNotes = async () => {
    setFlow(f => ({ ...f, notes: notesVal }))
    setEditingNotes(false)
    await api.flows.update(id, { notes: notesVal })
  }

  const deleteFlow = async () => {
    await api.flows.delete(id)
    window.dispatchEvent(new CustomEvent('flow-deleted', { detail: { flowId: id } }))
    navigate('/flows')
  }

  if (loading) return <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>Loading…</div>
  if (!flow) return <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>Flow not found.</div>

  return (
    <div>
      {/* Header */}
      <div style={{
        background: colors.card, border: `1px solid ${colors.border}`,
        borderRadius: '6px', padding: '14px 16px', marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
          <span style={{ fontFamily: FONT, fontSize: '15px', fontWeight: '600', color: colors.textPrimary, flex: 1 }}>
            {flow.flow_id}
          </span>
          <button onClick={cycleStatus} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }} title="Click to cycle status">
            <StatusBadge status={flow.status} />
          </button>
          {flow.flow_type && (
            <span style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim }}>
              [{flow.flow_type}]
            </span>
          )}
        </div>

        {/* From → To */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          padding: '10px', background: colors.bg, borderRadius: '4px', marginBottom: '12px',
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '2px' }}>From</div>
            <div style={{ fontFamily: FONT, fontSize: '12px', color: colors.textPrimary }}>{flow.from_company_name}</div>
            {flow.from_stream_name && (
              <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.textSecondary }}>{flow.from_stream_name}</div>
            )}
          </div>
          <span style={{ color: colors.textDim, fontSize: '16px' }}>→</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '2px' }}>To</div>
            <div style={{ fontFamily: FONT, fontSize: '12px', color: colors.textPrimary }}>{flow.to_company_name}</div>
            {flow.to_stream_name && (
              <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.textSecondary }}>{flow.to_stream_name}</div>
            )}
          </div>
        </div>

        <Field label="Flow rate" value={flow.flow_kton_per_year != null ? `${flow.flow_kton_per_year.toFixed(3)} kt/yr` : null} />

        {/* Notes */}
        <div style={{ marginBottom: '10px' }}>
          <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '4px' }}>Notes</div>
          {editingNotes ? (
            <div style={{ display: 'flex', gap: '6px' }}>
              <input
                autoFocus
                value={notesVal}
                onChange={e => setNotesVal(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') saveNotes(); if (e.key === 'Escape') setEditingNotes(false) }}
                style={{
                  flex: 1, fontFamily: FONT, fontSize: '12px',
                  background: colors.hover, border: `1px solid ${colors.accent}`,
                  color: colors.textPrimary, borderRadius: '3px', padding: '4px 8px',
                }}
              />
              <button onClick={saveNotes} style={{ fontFamily: FONT, fontSize: '11px', color: colors.scoreHigh, background: 'none', border: 'none', cursor: 'pointer' }}>Save</button>
              <button onClick={() => setEditingNotes(false)} style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, background: 'none', border: 'none', cursor: 'pointer' }}>Cancel</button>
            </div>
          ) : (
            <div
              onClick={() => { setEditingNotes(true); setNotesVal(flow.notes || '') }}
              style={{ fontFamily: FONT, fontSize: '12px', color: flow.notes ? colors.textSecondary : colors.textDim, cursor: 'text', padding: '2px 0' }}
            >
              {flow.notes || 'Add notes…'}
            </div>
          )}
        </div>
      </div>

      {/* Delete */}
      <div style={{ position: 'relative', display: 'inline-block' }}>
        <button
          onClick={() => setConfirmDelete(v => !v)}
          style={{
            fontFamily: FONT, fontSize: '11px', padding: '5px 12px',
            background: colors.scorePoor + '22', border: `1px solid ${colors.scorePoor}`,
            color: colors.scorePoor, borderRadius: '4px', cursor: 'pointer',
          }}
        >
          Delete Flow
        </button>
        {confirmDelete && (
          <ConfirmPopover
            message={`Permanently delete ${flow.flow_id}?`}
            onConfirm={deleteFlow}
            onCancel={() => setConfirmDelete(false)}
          />
        )}
      </div>
    </div>
  )
}
