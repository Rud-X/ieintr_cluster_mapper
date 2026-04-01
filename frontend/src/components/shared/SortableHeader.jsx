import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'

export default function SortableHeader({ label, field, sortField, sortDir, onSort, align = 'left' }) {
  const { colors } = useTheme()
  const active = sortField === field
  const arrow = active ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''
  return (
    <th
      onClick={() => onSort(field)}
      style={{
        fontFamily: FONT, fontSize: '11px', fontWeight: '600',
        color: active ? colors.accent : colors.textSecondary,
        padding: '8px 12px',
        textAlign: align,
        cursor: 'pointer',
        userSelect: 'none',
        whiteSpace: 'nowrap',
        borderBottom: `1px solid ${colors.border}`,
        background: colors.card,
        position: 'sticky', top: 0, zIndex: 1,
      }}
    >
      {label}{arrow}
    </th>
  )
}
