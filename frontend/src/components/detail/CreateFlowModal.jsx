import { useState, useEffect } from 'react'
import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import Modal from '../shared/Modal'
import { DirectionBadge } from '../shared/Badge'
import { api } from '../../lib/api'

const NODE_TYPE_LABELS = { import_source: 'IMP', export_sink: 'EXP', waste_facility: 'WMF' }

function genericLabel(nodeType) {
  return `Generic (${NODE_TYPE_LABELS[nodeType] ?? nodeType})`
}

/**
 * Props:
 *   company    - { company_id, name } — used when opened from StreamsTab (step 1 visible)
 *   prefill    - { fromStreamId, fromCompanyId } — partial: skip step 1
 *              - { fromStreamId, fromCompanyId, toStreamId, toCompanyId, ... } — full: show confirm screen
 *   onClose, onCreated
 */
export default function CreateFlowModal({ company, prefill, onClose, onCreated }) {
  const { colors } = useTheme()
  const fromCompanyId = prefill?.fromCompanyId ?? company?.company_id
  const isDirect = !!(prefill?.toCompanyId)
  const [step, setStep] = useState(isDirect ? 0 : prefill ? 2 : 1)
  const [sourceStream, setSourceStream] = useState(null)
  const [targetCompany, setTargetCompany] = useState(null)
  const [targetStream, setTargetStream] = useState(null)
  const [companies, setCompanies] = useState([])
  const [targetStreams, setTargetStreams] = useState([])
  const [working, setWorking] = useState(false)
  const [error, setError] = useState(null)

  // Company's own streams
  const [ownStreams, setOwnStreams] = useState([])
  useEffect(() => {
    api.companies.streams(fromCompanyId).then(streams => {
      setOwnStreams(streams)
      if (prefill?.fromStreamId) {
        const pre = streams.find(s => s.stream_id === prefill.fromStreamId)
        if (pre) setSourceStream(pre)
      }
    })
    api.companies.list().then(cs => setCompanies(cs.filter(c => c.company_id !== fromCompanyId && c.included)))
  }, [fromCompanyId])

  // When target company is picked, load their streams of opposite direction
  useEffect(() => {
    if (!targetCompany || !sourceStream) return
    const oppositeDir = sourceStream.direction === 'output' ? 'input' : 'output'
    api.companies.streams(targetCompany.company_id)
      .then(ss => setTargetStreams(ss.filter(s => s.direction === oppositeDir)))
  }, [targetCompany, sourceStream])

  const confirm = async () => {
    setWorking(true)
    setError(null)
    try {
      const isOutputSource = sourceStream.direction === 'output'
      const flow = await api.companies.createFlow(fromCompanyId, {
        from_stream_id: isOutputSource ? sourceStream.stream_id : targetStream.stream_id,
        to_stream_id: isOutputSource ? targetStream.stream_id : sourceStream.stream_id,
        from_company_id: isOutputSource ? fromCompanyId : targetCompany.company_id,
        to_company_id: isOutputSource ? targetCompany.company_id : fromCompanyId,
      })
      window.dispatchEvent(new CustomEvent('flow-created', { detail: { flow } }))
      onCreated?.()
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setWorking(false)
    }
  }

  const confirmDirect = async () => {
    setWorking(true)
    setError(null)
    try {
      const flow = await api.companies.createFlow(prefill.fromCompanyId, {
        from_stream_id: prefill.fromStreamId ?? null,
        to_stream_id: prefill.toStreamId ?? null,
        from_company_id: prefill.fromCompanyId,
        to_company_id: prefill.toCompanyId,
      })
      window.dispatchEvent(new CustomEvent('flow-created', { detail: { flow } }))
      onCreated?.()
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setWorking(false)
    }
  }

  function StreamRow({ stream, onClick, selected }) {
    return (
      <button
        onClick={onClick}
        style={{
          display: 'flex', alignItems: 'center', gap: '10px',
          padding: '7px 10px', width: '100%', textAlign: 'left',
          background: selected ? colors.accent + '22' : colors.hover,
          border: `1px solid ${selected ? colors.accent : colors.border}`,
          borderRadius: '4px', cursor: 'pointer', marginBottom: '4px',
        }}
      >
        <DirectionBadge direction={stream.direction} />
        <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, minWidth: '42px' }}>{stream.stream_id}</span>
        <span style={{ fontFamily: FONT, fontSize: '12px', color: colors.textPrimary, flex: 1 }}>{stream.stream_name}</span>
        <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textSecondary }}>
          {stream.flow_kton_per_year?.toFixed(3) ?? '—'} kt/yr
        </span>
      </button>
    )
  }

  const stepLabel = ['Confirm', 'Select source stream', 'Select target company', 'Select target stream'][step]
  const progress = step === 0 ? 'Confirm' : `Step ${step} / 3`

  return (
    <Modal title={`Create Flow — ${progress}: ${stepLabel}`} onClose={onClose}>
      {/* Breadcrumb */}
      {step > 0 && (sourceStream || targetCompany) && (
        <div style={{
          fontFamily: FONT, fontSize: '11px', color: colors.textDim,
          marginBottom: '12px', padding: '8px 10px',
          background: colors.bg, borderRadius: '4px', border: `1px solid ${colors.border}`,
        }}>
          {sourceStream && <span>Source: <span style={{ color: colors.textPrimary }}>{sourceStream.stream_name}</span> ({sourceStream.direction})</span>}
          {targetCompany && <span> → <span style={{ color: colors.textPrimary }}>{targetCompany.name}</span></span>}
          {targetStream && <span> / <span style={{ color: colors.textPrimary }}>{targetStream.stream_name}</span></span>}
        </div>
      )}

      {error && <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.scorePoor, marginBottom: '10px' }}>{error}</div>}

      {step === 0 && prefill && (
        <div>
          <div style={{
            background: colors.bg, border: `1px solid ${colors.border}`,
            borderRadius: '6px', padding: '14px 16px', marginBottom: '16px',
          }}>
            <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, marginBottom: '8px' }}>
              Create a flow between:
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <div style={{ fontFamily: FONT, fontSize: '12px', color: colors.textPrimary }}>
                <span style={{ color: colors.textDim, fontSize: '10px' }}>OUT </span>
                {prefill.fromStreamName ?? genericLabel(prefill.fromNodeType)}
              </div>
              <span style={{ color: colors.textDim }}>→</span>
              <div style={{ fontFamily: FONT, fontSize: '12px', color: colors.textPrimary }}>
                <span style={{ color: colors.textDim, fontSize: '10px' }}>IN </span>
                {prefill.toStreamName ?? genericLabel(prefill.toNodeType)}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            <button onClick={onClose} style={{
              fontFamily: FONT, fontSize: '12px', padding: '6px 14px',
              background: 'transparent', border: `1px solid ${colors.border}`,
              color: colors.textDim, borderRadius: '4px', cursor: 'pointer',
            }}>Cancel</button>
            <button onClick={confirmDirect} disabled={working} style={{
              fontFamily: FONT, fontSize: '12px', padding: '6px 16px',
              background: colors.accent, border: 'none', color: '#fff',
              borderRadius: '4px', cursor: working ? 'default' : 'pointer',
              opacity: working ? 0.6 : 1,
            }}>{working ? 'Creating…' : 'Confirm'}</button>
          </div>
        </div>
      )}

      {step === 1 && (
        <div>
          {ownStreams.map(s => (
            <StreamRow key={s.stream_id} stream={s} onClick={() => { setSourceStream(s); setStep(2) }} />
          ))}
        </div>
      )}

      {step === 2 && (
        <div>
          {companies.map(c => (
            <button
              key={c.company_id}
              onClick={() => { setTargetCompany(c); setStep(3) }}
              style={{
                display: 'flex', alignItems: 'center', gap: '10px',
                padding: '7px 10px', width: '100%', textAlign: 'left',
                background: colors.hover, border: `1px solid ${colors.border}`,
                borderRadius: '4px', cursor: 'pointer', marginBottom: '4px',
              }}
            >
              <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, minWidth: '42px' }}>{c.company_id}</span>
              <span style={{ fontFamily: FONT, fontSize: '12px', color: colors.textPrimary }}>{c.name}</span>
            </button>
          ))}
          <button
            onClick={() => { setStep(1); setSourceStream(null) }}
            style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, background: 'none', border: 'none', cursor: 'pointer', marginTop: '8px' }}
          >
            ← Back
          </button>
        </div>
      )}

      {step === 3 && (
        <div>
          {targetStreams.length === 0 ? (
            <div style={{ fontFamily: FONT, fontSize: '12px', color: colors.textDim }}>
              No compatible streams ({sourceStream.direction === 'output' ? 'input' : 'output'}) found for {targetCompany.name}.
            </div>
          ) : (
            targetStreams.map(s => (
              <StreamRow
                key={s.stream_id}
                stream={s}
                selected={targetStream?.stream_id === s.stream_id}
                onClick={() => setTargetStream(s)}
              />
            ))
          )}
          <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
            <button
              onClick={() => { setStep(2); setTargetCompany(null); setTargetStream(null) }}
              style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, background: 'none', border: 'none', cursor: 'pointer' }}
            >
              ← Back
            </button>
            <button
              onClick={confirm}
              disabled={!targetStream || working}
              style={{
                fontFamily: FONT, fontSize: '12px', padding: '6px 16px',
                background: targetStream ? colors.accent : colors.border,
                border: 'none', color: targetStream ? '#fff' : colors.textDim,
                borderRadius: '4px', cursor: targetStream ? 'pointer' : 'default',
                marginLeft: 'auto',
              }}
            >
              {working ? 'Creating…' : 'Create Flow'}
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}
