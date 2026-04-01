import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { DirectionBadge } from '../shared/Badge'
import { api } from '../../lib/api'

const UNKNOWN_ID = 'CM227'

export default function StreamDetail() {
  const { colors } = useTheme()
  const { id } = useParams()
  const [stream, setStream] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.streams.get(id).then(setStream).finally(() => setLoading(false))
  }, [id])

  if (loading) return <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>Loading…</div>
  if (!stream) return <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>Stream not found.</div>

  return (
    <div>
      <div style={{
        background: colors.card, border: `1px solid ${colors.border}`,
        borderRadius: '6px', padding: '14px 16px', marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
          <DirectionBadge direction={stream.direction} />
          <span style={{ fontFamily: FONT, fontSize: '15px', fontWeight: '600', color: colors.textPrimary, flex: 1 }}>
            {stream.stream_name}
          </span>
          <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim }}>{stream.stream_id}</span>
        </div>

        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '10px' }}>
          {[
            ['Company', stream.company_name || stream.company_id],
            ['Type', stream.stream_type || '—'],
            ['Flow', stream.norm_flow_kton_per_year != null ? `${stream.norm_flow_kton_per_year.toFixed(3)} kt/yr` : '—'],
            ['Carbon%', stream.carbon_pct != null ? `${(stream.carbon_pct * 100).toFixed(2)}%${stream.carbon_pct_complete === 0 ? ' (partial)' : ''}` : '—'],
          ].map(([label, value]) => (
            <div key={label}>
              <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '2px' }}>{label}</div>
              <div style={{ fontFamily: FONT, fontSize: '12px', color: colors.textSecondary }}>{value}</div>
            </div>
          ))}
          {stream.temperature_c != null && (
            <div>
              <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '2px' }}>Temp</div>
              <div style={{ fontFamily: FONT, fontSize: '12px', color: colors.textSecondary }}>{stream.temperature_c}°C</div>
            </div>
          )}
          {stream.pressure_bar != null && (
            <div>
              <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '2px' }}>Pressure</div>
              <div style={{ fontFamily: FONT, fontSize: '12px', color: colors.textSecondary }}>{stream.pressure_bar} bar</div>
            </div>
          )}
        </div>

        {stream.composition_raw && (
          <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginTop: '4px' }}>
            Raw: {stream.composition_raw}
          </div>
        )}
      </div>

      {/* Composition */}
      <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        Composition ({stream.composition?.length ?? 0} components)
      </div>

      {(!stream.composition || stream.composition.length === 0) ? (
        <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>No composition data.</div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['ID', 'Component', 'Fraction', 'Trace', 'C-frac'].map((h, i) => (
                <th key={h} style={{
                  fontFamily: FONT, fontSize: '10px', color: colors.textDim, fontWeight: '600',
                  padding: '5px 8px', textAlign: i === 0 || i === 1 ? 'left' : 'right',
                  borderBottom: `1px solid ${colors.border}`, background: colors.card,
                  position: 'sticky', top: 0,
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {stream.composition.map(row => {
              const isUnknown = row.component_id === UNKNOWN_ID
              const col = isUnknown || row.is_trace ? colors.textDim : colors.textSecondary
              return (
                <tr key={row.component_id}>
                  <td style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, padding: '4px 8px', borderBottom: `1px solid ${colors.border}` }}>{row.component_id}</td>
                  <td style={{ fontFamily: FONT, fontSize: '11px', color: col, padding: '4px 8px', borderBottom: `1px solid ${colors.border}` }}>
                    {row.name}{row.is_trace ? ' (trace)' : ''}
                  </td>
                  <td style={{ fontFamily: FONT, fontSize: '11px', color: col, padding: '4px 8px', textAlign: 'right', borderBottom: `1px solid ${colors.border}` }}>
                    {row.fraction != null ? row.fraction.toFixed(4) : '—'}
                  </td>
                  <td style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, padding: '4px 8px', textAlign: 'right', borderBottom: `1px solid ${colors.border}` }}>
                    {row.is_trace ? 'Y' : '—'}
                  </td>
                  <td style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, padding: '4px 8px', textAlign: 'right', borderBottom: `1px solid ${colors.border}` }}>
                    {row.carbon_fraction != null ? row.carbon_fraction.toFixed(4) : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
