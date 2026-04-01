import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'

export default function Tabs({ tabs, active, onChange }) {
  const { colors } = useTheme()
  return (
    <div style={{
      display: 'flex', gap: '0',
      borderBottom: `1px solid ${colors.border}`,
      marginBottom: '16px',
      flexShrink: 0,
    }}>
      {tabs.map(tab => (
        <button
          key={tab}
          onClick={() => onChange(tab)}
          style={{
            fontFamily: FONT, fontSize: '12px', fontWeight: active === tab ? '600' : '400',
            padding: '8px 14px',
            border: 'none',
            borderBottom: active === tab ? `2px solid ${colors.accent}` : '2px solid transparent',
            background: 'transparent',
            color: active === tab ? colors.textPrimary : colors.textSecondary,
            cursor: 'pointer',
            transition: 'color 0.15s',
            marginBottom: '-1px',
          }}
        >
          {tab}
        </button>
      ))}
    </div>
  )
}
