import { memo, useContext, useState } from 'react'
import { Handle, Position } from '@xyflow/react'
import { FONT, STREAM_TYPE_COLORS } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { ConnectingContext } from './ConnectingContext'

export function getCompanyColor(companyId) {
  const COMPANY_COLORS = [
    '#E8915A','#5B9BD5','#7BC67E','#D4A0D9',
    '#E06C75','#C9B458','#6CC1C8','#F28B82',
    '#A4C9A4','#B8A9C9','#D4956B','#8BB8D0',
  ]
  const n = parseInt(companyId.replace(/\D/g, ''), 10) || 0
  return COMPANY_COLORS[(n - 1) % COMPANY_COLORS.length]
}

const NODE_TYPE_LABELS = { import_source: 'IMP', export_sink: 'EXP', waste_facility: 'WMF' }
const EXTERNAL_TYPES = ['import_source', 'export_sink', 'waste_facility']
const GENERIC_DIR = { import_source: 'output', export_sink: 'input', waste_facility: 'input' }

function streamColor(stream) {
  return STREAM_TYPE_COLORS[stream.stream_type] ?? STREAM_TYPE_COLORS.default
}

function StreamHandle({ stream, index, total, side, companyId }) {
  const { colors } = useTheme()
  const connecting = useContext(ConnectingContext)
  const isInput = side === 'input'

  // Evenly space ports; map t ∈ [0,1] to calc position that clears the header
  // 48px reserved at top (header), 16px margin at bottom → ports in [48px, 100%-16px]
  const t = total === 1 ? 0.5 : index / (total - 1)
  const topStyle = `calc(80px + ${t} * (100% - 104px))`

  // Port color from stream type
  let handleColor = streamColor(stream)
  let showLabel = true
  let isCompatible = false

  if (connecting && connecting.sourceStreamId !== stream.stream_id) {
    isCompatible = (
      connecting.sourceCompanyId !== companyId &&
      connecting.sourceDirection !== stream.direction
    )
    if (isCompatible) {
      handleColor = colors.scoreHigh
      showLabel = true
    } else {
      handleColor = colors.textDim
    }
  }

  const handleOpacity = connecting ? (isCompatible ? 1 : 0.25) : 1

  return (
    <>
      <Handle
        type={isInput ? 'target' : 'source'}
        position={isInput ? Position.Left : Position.Right}
        id={stream.stream_id}
        style={{
          top: topStyle,
          [isInput ? 'left' : 'right']: '-5px',
          width: '10px',
          height: '10px',
          background: handleColor,
          border: `2px solid ${handleColor}`,
          borderRadius: '50%',
          opacity: handleOpacity,
          transition: 'opacity 0.15s, background 0.15s',
          cursor: 'crosshair',
        }}
      />
      {showLabel && (
        <div style={{
          position: 'absolute',
          top: topStyle,
          [isInput ? 'left' : 'right']: '14px',
          transform: 'translateY(-50%)',
          fontFamily: FONT, fontSize: '9px',
          color: isCompatible ? colors.scoreHigh : handleColor,
          whiteSpace: 'nowrap', pointerEvents: 'none',
          background: colors.card, padding: '1px 3px', borderRadius: '2px',
        }}>
          {stream.stream_name}
        </div>
      )}
    </>
  )
}

const CompanyNode = memo(({ data, selected }) => {
  const { colors } = useTheme()
  const color = getCompanyColor(data.company_id)
  const inputs  = (data.streams || []).filter(s => s.direction === 'input')
  const outputs = (data.streams || []).filter(s => s.direction === 'output')
  const typeLabel = NODE_TYPE_LABELS[data.node_type]
  const isExternal = EXTERNAL_TYPES.includes(data.node_type)
  const genericSide = isExternal ? GENERIC_DIR[data.node_type] : null
  const [hovered, setHovered] = useState(false)

  const minHeight = Math.max(100, Math.max(inputs.length, outputs.length) * 24 + 104)

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: colors.card,
        border: `2px solid ${selected ? color : hovered ? color + '66' : colors.border}`,
        borderRadius: '6px',
        padding: '10px 14px',
        minWidth: '180px',
        maxWidth: '220px',
        minHeight: `${minHeight}px`,
        cursor: 'default',
        boxShadow: selected
          ? `0 0 0 2px ${color}66, 0 0 12px ${color}44`
          : hovered
            ? `0 0 0 1px ${color}44, 0 2px 12px ${color}33`
            : '0 2px 8px rgba(0,0,0,0.4)',
        transition: 'border-color 0.15s, box-shadow 0.15s',
        position: 'relative',
      }}
    >
      {/* Colored top bar — always visible */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0,
        height: '3px',
        background: color,
        borderRadius: '4px 4px 0 0',
        pointerEvents: 'none',
      }} />
      {inputs.map((s, i) => (
        <StreamHandle key={s.stream_id} stream={s} index={i} total={inputs.length}
          side="input" companyId={data.company_id} />
      ))}
      {outputs.map((s, i) => (
        <StreamHandle key={s.stream_id} stream={s} index={i} total={outputs.length}
          side="output" companyId={data.company_id} />
      ))}
      {isExternal && (
        <>
          <Handle
            type={genericSide === 'input' ? 'target' : 'source'}
            position={genericSide === 'input' ? Position.Left : Position.Right}
            id={`generic-${data.company_id}`}
            style={{
              top: '50%',
              [genericSide === 'input' ? 'left' : 'right']: '-5px',
              width: '12px',
              height: '12px',
              background: colors.textDim,
              border: `2px dashed ${colors.textDim}`,
              borderRadius: '50%',
            }}
          />
          <div style={{
            position: 'absolute',
            top: '50%',
            [genericSide === 'input' ? 'left' : 'right']: '14px',
            transform: 'translateY(-50%)',
            fontFamily: FONT, fontSize: '9px',
            color: colors.textDim,
            whiteSpace: 'nowrap', pointerEvents: 'none',
            background: colors.card, padding: '1px 3px', borderRadius: '2px',
          }}>ANY</div>
        </>
      )}

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', marginBottom: '4px' }}>
        <span style={{ fontFamily: FONT, fontSize: '12px', fontWeight: '600', color: colors.textPrimary, flex: 1, lineHeight: '1.3' }}>
          {data.label}
        </span>
        {typeLabel && (
          <span style={{
            fontFamily: FONT, fontSize: '9px', color,
            border: `1px solid ${color}`, borderRadius: '3px',
            padding: '1px 4px', flexShrink: 0, marginTop: '1px',
          }}>
            {typeLabel}
          </span>
        )}
      </div>

      {data.sector && (
        <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '6px' }}>
          {data.sector}
        </div>
      )}

      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
        {inputs.length > 0 && (
          <span style={{
            fontFamily: FONT, fontSize: '9px', color: STREAM_TYPE_COLORS.raw_material,
            background: STREAM_TYPE_COLORS.raw_material + '18', border: `1px solid ${STREAM_TYPE_COLORS.raw_material}44`,
            borderRadius: '3px', padding: '1px 5px',
          }}>↓ {inputs.length}</span>
        )}
        {outputs.length > 0 && (
          <span style={{
            fontFamily: FONT, fontSize: '9px', color: STREAM_TYPE_COLORS.products,
            background: STREAM_TYPE_COLORS.products + '18', border: `1px solid ${STREAM_TYPE_COLORS.products}44`,
            borderRadius: '3px', padding: '1px 5px',
          }}>↑ {outputs.length}</span>
        )}
      </div>
    </div>
  )
})

CompanyNode.displayName = 'CompanyNode'
export default CompanyNode
