import { useTheme } from '../../lib/ThemeContext'
import { FONT } from '../../lib/theme'

export default function ThemeFAB() {
  const { theme, colors, toggleTheme } = useTheme()
  return (
    <button
      onClick={toggleTheme}
      title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      style={{
        position: 'fixed',
        bottom: '80px',
        left: '20px',
        width: '52px',
        height: '52px',
        borderRadius: '50%',
        background: colors.card,
        border: `2px solid ${colors.accent}`,
        color: colors.accent,
        fontFamily: FONT,
        fontSize: '20px',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
        zIndex: 100,
        transition: 'border-color 0.15s, background 0.15s',
      }}
      onMouseEnter={e => { e.currentTarget.style.background = colors.hover }}
      onMouseLeave={e => { e.currentTarget.style.background = colors.card }}
    >
      {theme === 'dark' ? '☀' : '🌙'}
    </button>
  )
}
