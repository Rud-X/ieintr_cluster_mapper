import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import ViewToggle from './ViewToggle'

const TABS = ['Companies', 'Flows', 'Streams', 'Components']

export default function LeftPanel({ view, onViewChange, tab, onTabChange, onlyIncluded, onToggleIncluded, children }) {
  const { colors } = useTheme()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Top bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '10px 16px',
        borderBottom: `1px solid ${colors.border}`,
        background: colors.card,
        flexShrink: 0,
      }}>
        <span style={{ fontFamily: FONT, fontSize: '13px', color: colors.textPrimary, fontWeight: '600', marginRight: '4px' }}>
          Industrial Cluster
        </span>
        <ViewToggle view={view} onChange={onViewChange} />

        {/* Table tabs — only shown in table view */}
        {view === 'table' && (
          <div style={{ display: 'flex', gap: '2px', marginLeft: '8px' }}>
            {TABS.map(t => (
              <button key={t} onClick={() => onTabChange(t)} style={{
                fontFamily: FONT,
                fontSize: '11px',
                padding: '4px 10px',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                background: tab === t ? colors.hover : 'transparent',
                color: tab === t ? colors.textPrimary : colors.textSecondary,
                borderBottom: tab === t ? `2px solid ${colors.accent}` : '2px solid transparent',
                transition: 'all 0.15s',
              }}>
                {t}
              </button>
            ))}
          </div>
        )}
        {view === 'table' && (
          <button onClick={onToggleIncluded} style={{
            marginLeft: 'auto',
            fontFamily: FONT,
            fontSize: '11px',
            padding: '4px 10px',
            border: `1px solid ${onlyIncluded ? colors.accent : colors.border}`,
            borderRadius: '4px',
            cursor: 'pointer',
            background: onlyIncluded ? colors.accent + '22' : 'transparent',
            color: onlyIncluded ? colors.accent : colors.textSecondary,
            transition: 'all 0.15s',
            whiteSpace: 'nowrap',
          }}>
            {onlyIncluded ? '● Included only' : '○ Included only'}
          </button>
        )}
      </div>

      {/* Content area */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {children}
      </div>
    </div>
  )
}
