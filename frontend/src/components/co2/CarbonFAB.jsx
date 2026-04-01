import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'

export default function CarbonFAB({ onClick }) {
  const { colors } = useTheme()
  return (
    <button
      onClick={onClick}
      title="Carbon Accounting"
      style={{
        position: 'fixed',
        bottom: '20px',
        left: '20px',
        width: '52px',
        height: '52px',
        borderRadius: '50%',
        background: colors.card,
        border: `2px solid ${colors.accent}`,
        color: colors.accent,
        fontFamily: FONT,
        fontSize: '11px',
        fontWeight: '700',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        letterSpacing: '0.02em',
        boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
        zIndex: 100,
        transition: 'border-color 0.15s, background 0.15s',
      }}
      onMouseEnter={e => { e.currentTarget.style.background = colors.hover }}
      onMouseLeave={e => { e.currentTarget.style.background = colors.card }}
    >
      CO₂
    </button>
  )
}
