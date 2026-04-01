import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'

export default function ViewToggle({ view, onChange }) {
  const { colors } = useTheme()
  const btn = (label, val) => ({
    fontFamily: FONT,
    fontSize: '12px',
    padding: '5px 14px',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    background: view === val ? colors.accent : 'transparent',
    color: view === val ? '#fff' : colors.textSecondary,
    fontWeight: view === val ? '600' : '400',
    transition: 'background 0.15s, color 0.15s',
  })

  return (
    <div style={{
      display: 'flex',
      background: colors.card,
      border: `1px solid ${colors.border}`,
      borderRadius: '6px',
      padding: '3px',
      gap: '2px',
    }}>
      <button style={btn('Table', 'table')} onClick={() => onChange('table')}>Table</button>
      <button style={btn('Graph', 'graph')} onClick={() => onChange('graph')}>Graph</button>
    </div>
  )
}
