import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { useNavigate } from 'react-router-dom'

export default function DetailPanel({ children, onClose }) {
  const { colors } = useTheme()
  const navigate = useNavigate()

  const handleClose = () => {
    if (onClose) onClose()
    else navigate(-1)
  }

  return (
    <div className="slide-in" style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: colors.bg,
      overflow: 'hidden',
    }}>
      {/* Detail panel header bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        padding: '10px 16px',
        borderBottom: `1px solid ${colors.border}`,
        background: colors.card,
        flexShrink: 0,
      }}>
        <button onClick={handleClose} style={{
          fontFamily: FONT,
          fontSize: '12px',
          padding: '4px 10px',
          border: `1px solid ${colors.border}`,
          borderRadius: '4px',
          background: 'transparent',
          color: colors.textSecondary,
          cursor: 'pointer',
        }}>
          ✕ Close
        </button>
      </div>

      {/* Scrollable content */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        scrollbarWidth: 'thin',
        scrollbarColor: `${colors.border} transparent`,
      }}>
        {children}
      </div>
    </div>
  )
}
