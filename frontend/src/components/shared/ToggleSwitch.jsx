import { useTheme } from '../../lib/ThemeContext'

export default function ToggleSwitch({ checked, onChange, disabled }) {
  const { colors } = useTheme()
  return (
    <div
      onClick={disabled ? undefined : () => onChange(!checked)}
      style={{
        width: '32px', height: '18px',
        borderRadius: '9px',
        background: checked ? colors.scoreHigh : colors.border,
        position: 'relative',
        cursor: disabled ? 'default' : 'pointer',
        transition: 'background 0.2s',
        flexShrink: 0,
      }}
    >
      <div style={{
        position: 'absolute',
        top: '2px',
        left: checked ? '16px' : '2px',
        width: '14px', height: '14px',
        borderRadius: '50%',
        background: '#fff',
        transition: 'left 0.2s',
      }} />
    </div>
  )
}
