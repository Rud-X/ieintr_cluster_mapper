import { useState, useEffect, useCallback } from 'react'
import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { api } from '../../lib/api'

function StatusRow({ label, value, total }) {
  const { colors } = useTheme()
  const pct = total ? Math.round((value / total) * 100) : 0
  return (
    <div style={{ marginBottom: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
        <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textSecondary }}>{label}</span>
        <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim }}>{value} / {total} ({pct}%)</span>
      </div>
      <div style={{ height: '4px', background: colors.border, borderRadius: '2px' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: pct === 100 ? colors.scoreHigh : pct > 70 ? colors.scoreMid : colors.scoreLow, borderRadius: '2px', transition: 'width 0.3s' }} />
      </div>
    </div>
  )
}

function GapRow({ gap, onUpdated }) {
  const { colors } = useTheme()
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState('')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    const n = parseFloat(val)
    if (isNaN(n)) return
    setSaving(true)
    try {
      await api.components.update(gap.component_id, { carbon_pct: n })
      onUpdated()
    } finally {
      setSaving(false)
      setEditing(false)
    }
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '8px',
      padding: '5px 8px', borderRadius: '4px',
      background: colors.bg, marginBottom: '2px',
    }}>
      <span style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, minWidth: '42px' }}>{gap.component_id}</span>
      <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textSecondary, flex: 1 }}>{gap.name}</span>
      <span style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, minWidth: '28px', textAlign: 'right' }}>{gap.stream_count}</span>
      {editing ? (
        <>
          <input
            autoFocus
            placeholder="0.xx"
            value={val}
            onChange={e => setVal(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') setEditing(false) }}
            style={{
              width: '60px', fontFamily: FONT, fontSize: '11px',
              background: colors.hover, border: `1px solid ${colors.accent}`,
              color: colors.textPrimary, borderRadius: '3px', padding: '2px 5px',
            }}
          />
          <button onClick={save} disabled={saving} style={{ fontFamily: FONT, fontSize: '10px', color: colors.scoreHigh, background: 'none', border: 'none', cursor: 'pointer' }}>✓</button>
          <button onClick={() => setEditing(false)} style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
        </>
      ) : (
        <button
          onClick={() => { setEditing(true); setVal('') }}
          style={{
            fontFamily: FONT, fontSize: '10px', padding: '2px 6px',
            background: colors.hover, border: `1px solid ${colors.border}`,
            color: colors.textDim, borderRadius: '3px', cursor: 'pointer',
          }}
        >
          Set C%
        </button>
      )}
    </div>
  )
}

export default function CarbonPanel({ onClose }) {
  const { colors } = useTheme()
  const [status, setStatus] = useState(null)
  const [gaps, setGaps] = useState([])
  const [loading, setLoading] = useState(true)
  const [recalcWorking, setRecalcWorking] = useState(false)
  const [showAllGaps, setShowAllGaps] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, g] = await Promise.all([api.carbon.status(), api.carbon.gaps()])
      setStatus(s)
      setGaps(g)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const recalculate = async () => {
    setRecalcWorking(true)
    try {
      await api.carbon.recalculate()
      await load()
    } finally {
      setRecalcWorking(false)
    }
  }

  const actionableGaps = gaps.filter(g => !g.needs_review)
  const displayGaps = showAllGaps ? gaps : actionableGaps.slice(0, 10)

  return (
    <div style={{
      position: 'fixed', bottom: '84px', left: '20px', width: '400px',
      maxHeight: '70vh',
      background: colors.card, border: `1px solid ${colors.border}`,
      borderRadius: '8px', boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      zIndex: 101, display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 16px', borderBottom: `1px solid ${colors.border}`, flexShrink: 0,
      }}>
        <span style={{ fontFamily: FONT, fontSize: '12px', fontWeight: '600', color: colors.textPrimary }}>
          Carbon Accounting
        </span>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={recalculate}
            disabled={recalcWorking}
            style={{
              fontFamily: FONT, fontSize: '10px', padding: '3px 8px',
              background: colors.accent + '22', border: `1px solid ${colors.accent}`,
              color: colors.accent, borderRadius: '3px', cursor: 'pointer',
            }}
          >
            {recalcWorking ? 'Recalculating…' : 'Recalculate'}
          </button>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: colors.textDim, cursor: 'pointer', fontFamily: FONT, fontSize: '12px' }}>✕</button>
        </div>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px' }}>
        {loading ? (
          <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>Loading…</div>
        ) : (
          <>
            {/* Coverage stats */}
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Coverage</div>
              <StatusRow
                label="Components with carbon%"
                value={status.formula_components + status.manual_components}
                total={status.total_components}
              />
              <StatusRow
                label="Streams with carbon%"
                value={status.streams_with_carbon}
                total={status.total_streams}
              />
            </div>

            {/* Gaps */}
            {actionableGaps.length > 0 && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                    Actionable Gaps ({actionableGaps.length})
                  </div>
                  <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim }}>streams</div>
                </div>
                {displayGaps.map(g => (
                  <GapRow key={g.component_id} gap={g} onUpdated={load} />
                ))}
                {actionableGaps.length > 10 && (
                  <button
                    onClick={() => setShowAllGaps(v => !v)}
                    style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, background: 'none', border: 'none', cursor: 'pointer', marginTop: '6px' }}
                  >
                    {showAllGaps ? 'Show fewer' : `Show all ${actionableGaps.length}…`}
                  </button>
                )}
              </div>
            )}
            {actionableGaps.length === 0 && (
              <div style={{ fontFamily: FONT, fontSize: '12px', color: colors.scoreHigh }}>
                ✓ No actionable gaps remaining.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
