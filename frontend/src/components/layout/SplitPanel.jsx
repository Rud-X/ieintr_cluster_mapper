import { useTheme } from '../../lib/ThemeContext'

export default function SplitPanel({ left, right, showRight }) {
  const { colors } = useTheme()
  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      width: '100vw',
      overflow: 'hidden',
      background: colors.bg,
    }}>
      {/* Left panel */}
      <div style={{
        flex: showRight ? '0 0 55%' : '1',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        borderRight: showRight ? `1px solid ${colors.border}` : 'none',
        transition: 'flex 0.15s',
      }}>
        {left}
      </div>

      {/* Right detail panel */}
      {showRight && (
        <div style={{
          flex: '1',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}>
          {right}
        </div>
      )}
    </div>
  )
}
