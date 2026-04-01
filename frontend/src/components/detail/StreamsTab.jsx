import { useState, useEffect } from 'react'
import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { DirectionBadge } from '../shared/Badge'
import { api } from '../../lib/api'

const UNKNOWN_ID = 'CM227'

function CompositionTable({ streamId }) {
  const { colors } = useTheme()
  const [data, setData] = useState(null)

  useEffect(() => {
    api.streams.get(streamId).then(s => setData(s.composition))
  }, [streamId])

  if (!data) return (
    <div style={{ padding: '8px 12px', color: colors.textDim, fontFamily: FONT, fontSize: '11px' }}>Loading…</div>
  )
  if (data.length === 0) return (
    <div style={{ padding: '8px 12px', color: colors.textDim, fontFamily: FONT, fontSize: '11px' }}>No composition data.</div>
  )

  return (
    <div style={{ padding: '4px 0 8px 32px' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {['ID', 'Component', 'Fraction', 'Trace', 'C-frac'].map(h => (
              <th key={h} style={{
                fontFamily: FONT, fontSize: '10px', color: colors.textDim,
                padding: '4px 8px', textAlign: h === 'ID' ? 'left' : 'right',
                borderBottom: `1px solid ${colors.border}`, fontWeight: '600',
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map(row => {
            const isUnknown = row.component_id === UNKNOWN_ID
            const color = isUnknown ? colors.textDim : (row.is_trace ? colors.textDim : colors.textSecondary)
            return (
              <tr key={row.component_id}>
                <td style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, padding: '3px 8px' }}>{row.component_id}</td>
                <td style={{ fontFamily: FONT, fontSize: '11px', color, padding: '3px 8px' }}>
                  {row.name}{row.is_trace ? ' (trace)' : ''}
                </td>
                <td style={{ fontFamily: FONT, fontSize: '11px', color, padding: '3px 8px', textAlign: 'right' }}>
                  {row.fraction != null ? row.fraction.toFixed(4) : '—'}
                </td>
                <td style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, padding: '3px 8px', textAlign: 'right' }}>
                  {row.is_trace ? 'Y' : '—'}
                </td>
                <td style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, padding: '3px 8px', textAlign: 'right' }}>
                  {row.carbon_fraction != null ? row.carbon_fraction.toFixed(4) : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function StreamsTab({ companyId, onCreateFlow, onCreateFlowFromStream }) {
  const { colors } = useTheme()
  const [streams, setStreams] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)

  useEffect(() => {
    setLoading(true)
    api.companies.streams(companyId)
      .then(setStreams)
      .finally(() => setLoading(false))
  }, [companyId])

  const toggle = (id) => setExpanded(e => e === id ? null : id)

  if (loading) return <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>Loading…</div>
  if (streams.length === 0) return <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>No streams.</div>

  const inputs = streams.filter(s => s.direction === 'input')
  const outputs = streams.filter(s => s.direction === 'output')

  const renderGroup = (group, label) => {
    if (group.length === 0) return null
    return (
      <div style={{ marginBottom: '16px' }}>
        <div style={{
          fontFamily: FONT, fontSize: '10px', fontWeight: '600',
          color: colors.textDim, letterSpacing: '0.08em', textTransform: 'uppercase',
          padding: '0 0 6px 0', marginBottom: '2px',
          borderBottom: `1px solid ${colors.border}`,
        }}>{label} ({group.length})</div>
        {group.map(s => {
          const isOpen = expanded === s.stream_id
          return (
            <div key={s.stream_id}>
              <div
                onClick={() => toggle(s.stream_id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '7px 8px', cursor: 'pointer', borderRadius: '4px',
                  background: isOpen ? colors.hover : 'transparent',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={e => { if (!isOpen) e.currentTarget.style.background = colors.hover + '66' }}
                onMouseLeave={e => { if (!isOpen) e.currentTarget.style.background = 'transparent' }}
              >
                <span style={{ color: colors.textDim, fontFamily: FONT, fontSize: '11px', width: '12px' }}>
                  {isOpen ? '▾' : '▸'}
                </span>
                <DirectionBadge direction={s.direction} />
                <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, minWidth: '42px' }}>
                  {s.stream_id}
                </span>
                <span style={{ fontFamily: FONT, fontSize: '12px', color: colors.textPrimary, flex: 1 }}>
                  {s.stream_name}
                </span>
                <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textSecondary, minWidth: '80px', textAlign: 'right' }}>
                  {s.norm_flow_kton_per_year != null ? `${s.norm_flow_kton_per_year.toFixed(3)} kt/yr` : '—'}
                </span>
                {s.carbon_pct != null && (
                  <span style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, minWidth: '50px', textAlign: 'right' }}>
                    C:{(s.carbon_pct * 100).toFixed(1)}%{s.carbon_pct_complete === 0 ? '*' : ''}
                  </span>
                )}
                {onCreateFlowFromStream && (
                  <button
                    onClick={e => { e.stopPropagation(); onCreateFlowFromStream(s) }}
                    title="Create flow from this stream"
                    style={{
                      fontFamily: FONT, fontSize: '10px', padding: '2px 6px',
                      background: 'transparent', border: `1px solid ${colors.border}`,
                      color: colors.textDim, borderRadius: '3px', cursor: 'pointer',
                      flexShrink: 0,
                    }}
                  >→ Flow</button>
                )}
              </div>
              {isOpen && <CompositionTable streamId={s.stream_id} />}
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '12px' }}>
        <button
          onClick={onCreateFlow}
          style={{
            fontFamily: FONT, fontSize: '11px', padding: '5px 12px',
            background: colors.accent + '22', border: `1px solid ${colors.accent}`,
            color: colors.accent, borderRadius: '4px', cursor: 'pointer',
          }}
        >
          + Create Flow
        </button>
      </div>
      {renderGroup(inputs, 'Inputs')}
      {renderGroup(outputs, 'Outputs')}
    </div>
  )
}
