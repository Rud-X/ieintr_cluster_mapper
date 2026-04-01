import { FONT, NODE_TYPE_COLORS, STATUS_COLORS } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'

const NODE_TYPE_LABELS = {
  company: null,
  import_source: 'IMP',
  export_sink: 'EXP',
  waste_facility: 'WMF',
}

export function NodeTypeBadge({ nodeType }) {
  const label = NODE_TYPE_LABELS[nodeType]
  if (!label) return null
  return (
    <span style={{
      fontFamily: FONT, fontSize: '10px', fontWeight: '600',
      padding: '2px 5px', borderRadius: '3px',
      background: NODE_TYPE_COLORS[nodeType] + '22',
      color: NODE_TYPE_COLORS[nodeType],
      border: `1px solid ${NODE_TYPE_COLORS[nodeType]}55`,
    }}>
      {label}
    </span>
  )
}

export function StatusBadge({ status }) {
  const { colors } = useTheme()
  const color = STATUS_COLORS[status] || colors.textDim
  return (
    <span style={{
      fontFamily: FONT, fontSize: '10px', fontWeight: '600',
      padding: '2px 6px', borderRadius: '10px',
      background: color + '22',
      color: color,
      border: `1px solid ${color}55`,
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
    }}>
      {status}
    </span>
  )
}

export function DirectionBadge({ direction }) {
  const { colors } = useTheme()
  const color = direction === 'input' ? colors.accent : '#7BC67E'
  return (
    <span style={{
      fontFamily: FONT, fontSize: '10px', fontWeight: '600',
      padding: '2px 5px', borderRadius: '3px',
      background: color + '22', color,
      border: `1px solid ${color}55`,
    }}>
      {direction === 'input' ? '→ IN' : 'OUT →'}
    </span>
  )
}

export function IncludedBadge({ included }) {
  const { colors } = useTheme()
  const color = included ? colors.scoreHigh : colors.scorePoor
  return (
    <span style={{
      fontFamily: FONT, fontSize: '10px', fontWeight: '700',
      padding: '2px 7px', borderRadius: '10px',
      background: color + '22', color,
      border: `1px solid ${color}55`,
    }}>
      {included ? 'Y' : 'N'}
    </span>
  )
}
