import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { api } from '../../lib/api'

function Field({ label, children }) {
  const { colors } = useTheme()
  return (
    <div style={{ marginBottom: '10px' }}>
      <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '2px' }}>{label}</div>
      <div style={{ fontFamily: FONT, fontSize: '12px', color: colors.textSecondary }}>{children ?? '—'}</div>
    </div>
  )
}

function EditableNumber({ label, value, onSave }) {
  const { colors } = useTheme()
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState('')

  const save = () => {
    const n = parseFloat(val)
    if (!isNaN(n)) onSave(n)
    setEditing(false)
  }

  return (
    <div style={{ marginBottom: '10px' }}>
      <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '4px' }}>{label}</div>
      {editing ? (
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <input
            autoFocus
            value={val}
            onChange={e => setVal(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') setEditing(false) }}
            style={{
              width: '100px', fontFamily: FONT, fontSize: '12px',
              background: colors.hover, border: `1px solid ${colors.accent}`,
              color: colors.textPrimary, borderRadius: '3px', padding: '3px 6px',
            }}
          />
          <button onClick={save} style={{ fontFamily: FONT, fontSize: '11px', color: colors.scoreHigh, background: 'none', border: 'none', cursor: 'pointer' }}>Save</button>
          <button onClick={() => setEditing(false)} style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, background: 'none', border: 'none', cursor: 'pointer' }}>Cancel</button>
        </div>
      ) : (
        <div
          onClick={() => { setVal(value != null ? String(value) : ''); setEditing(true) }}
          style={{ fontFamily: FONT, fontSize: '12px', color: value != null ? colors.textSecondary : colors.textDim, cursor: 'text' }}
        >
          {value != null ? value : 'Click to set…'}
        </div>
      )}
    </div>
  )
}

export default function ComponentDetail() {
  const { colors } = useTheme()
  const { id } = useParams()
  const [comp, setComp] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)

  const load = () => {
    setLoading(true)
    api.components.get(id).then(setComp).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [id])

  const update = async (body) => {
    setSaving(true)
    setMessage(null)
    try {
      const updated = await api.components.update(id, body)
      setComp(updated)
      setMessage('Saved. Carbon values recalculated.')
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    } finally {
      setSaving(false)
    }
  }

  const clearOverride = () => update({ clear_override: true })

  if (loading) return <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>Loading…</div>
  if (!comp) return <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>Component not found.</div>

  return (
    <div>
      {/* Header card */}
      <div style={{
        background: colors.card, border: `1px solid ${colors.border}`,
        borderRadius: '6px', padding: '14px 16px', marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
          <span style={{ fontFamily: FONT, fontSize: '15px', fontWeight: '600', color: colors.textPrimary, flex: 1 }}>
            {comp.name}
          </span>
          <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim }}>{comp.component_id}</span>
          {comp.needs_review ? (
            <span style={{ fontFamily: FONT, fontSize: '10px', color: colors.scoreLow, border: `1px solid ${colors.scoreLow}`, borderRadius: '3px', padding: '2px 5px' }}>
              needs review
            </span>
          ) : null}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 20px' }}>
          <Field label="Category">{comp.category}</Field>
          <Field label="CAS">{comp.cas_number}</Field>
          <Field label="Aliases">
            <span style={{ color: colors.textDim, fontSize: '11px' }}>{comp.aliases || '—'}</span>
          </Field>
          <Field label="Hazardous">{comp.hazardous === 1 ? 'Yes' : comp.hazardous === 0 ? 'No' : '—'}</Field>
        </div>
      </div>

      {/* Carbon data */}
      <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        Carbon Data
      </div>
      <div style={{
        background: colors.card, border: `1px solid ${colors.border}`,
        borderRadius: '6px', padding: '14px 16px', marginBottom: '16px',
      }}>
        <EditableNumber
          label="Carbon atoms"
          value={comp.carbon_atoms}
          onSave={v => update({ carbon_atoms: Math.round(v) })}
        />
        <EditableNumber
          label="Molecular weight (g/mol)"
          value={comp.molecular_weight}
          onSave={v => update({ molecular_weight: v })}
        />

        <div style={{ marginBottom: '10px' }}>
          <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '4px' }}>
            Carbon weight % {comp.carbon_weight_pct_manual ? '(manual override)' : '(formula-derived)'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontFamily: FONT, fontSize: '12px', color: comp.carbon_weight_pct != null ? colors.textSecondary : colors.scorePoor }}>
              {comp.carbon_weight_pct != null ? `${(comp.carbon_weight_pct * 100).toFixed(4)}%` : 'NULL'}
            </span>
            {comp.carbon_weight_pct_manual ? (
              <button
                onClick={clearOverride}
                disabled={saving}
                style={{
                  fontFamily: FONT, fontSize: '10px', padding: '2px 7px',
                  background: 'transparent', border: `1px solid ${colors.border}`,
                  color: colors.textDim, borderRadius: '3px', cursor: 'pointer',
                }}
              >
                Clear override
              </button>
            ) : null}
          </div>
        </div>

        {/* Manual override */}
        <EditableNumber
          label="Manual carbon % override (0–1 scale, e.g. 0.27 = 27%)"
          value={null}
          onSave={v => update({ carbon_pct: v })}
        />

        {message && (
          <div style={{ fontFamily: FONT, fontSize: '11px', color: message.startsWith('Error') ? colors.scorePoor : colors.scoreHigh, marginTop: '8px' }}>
            {message}
          </div>
        )}
      </div>

      {comp.notes && (
        <Field label="Notes">{comp.notes}</Field>
      )}
    </div>
  )
}
