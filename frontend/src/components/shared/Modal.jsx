import { useEffect } from 'react'
import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'

export default function Modal({ title, onClose, children, width = '520px' }) {
  const { colors } = useTheme()

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 200,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width, maxHeight: '80vh',
          background: colors.card,
          border: `1px solid ${colors.border}`,
          borderRadius: '8px',
          display: 'flex', flexDirection: 'column',
          boxShadow: '0 16px 48px rgba(0,0,0,0.6)',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 18px',
          borderBottom: `1px solid ${colors.border}`,
          flexShrink: 0,
        }}>
          <span style={{ fontFamily: FONT, fontSize: '13px', fontWeight: '600', color: colors.textPrimary }}>
            {title}
          </span>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: colors.textDim,
            cursor: 'pointer', fontFamily: FONT, fontSize: '14px', lineHeight: 1,
          }}>✕</button>
        </div>
        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '18px' }}>
          {children}
        </div>
      </div>
    </div>
  )
}
