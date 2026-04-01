import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'

export default function ConfirmPopover({ message, onConfirm, onCancel }) {
  const { colors } = useTheme()
  return (
    <div style={{
      position: 'absolute', zIndex: 50, right: 0, top: '100%', marginTop: '4px',
      background: colors.card, border: `1px solid ${colors.border}`,
      borderRadius: '6px', padding: '12px 14px',
      boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
      minWidth: '200px',
    }}>
      <p style={{ fontFamily: FONT, fontSize: '12px', color: colors.textPrimary, marginBottom: '10px' }}>
        {message}
      </p>
      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
        <button onClick={onCancel} style={{
          fontFamily: FONT, fontSize: '11px', padding: '4px 10px',
          background: 'transparent', border: `1px solid ${colors.border}`,
          color: colors.textSecondary, borderRadius: '4px', cursor: 'pointer',
        }}>Cancel</button>
        <button onClick={onConfirm} style={{
          fontFamily: FONT, fontSize: '11px', padding: '4px 10px',
          background: colors.scorePoor + '33', border: `1px solid ${colors.scorePoor}`,
          color: colors.scorePoor, borderRadius: '4px', cursor: 'pointer',
        }}>Delete</button>
      </div>
    </div>
  )
}
