import { useState, useEffect } from 'react'
import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { api } from '../../lib/api'

export default function NormalizationTab({ companyId, company, onCompanyUpdated }) {
  const { colors } = useTheme()
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [message, setMessage] = useState(null)
  const [editingSetpoint, setEditingSetpoint] = useState(false)
  const [setpointInput, setSetpointInput] = useState('')
  const [editingCustomFactor, setEditingCustomFactor] = useState(false)
  const [customFactorInput, setCustomFactorInput] = useState('')

  const load = () => {
    setLoading(true)
    api.companies.normalization.candidates(companyId)
      .then(setCandidates)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [companyId])

  const setRef = async (streamId) => {
    setWorking(true)
    try {
      if (company?.normalize_stream_id === streamId) {
        await api.companies.normalization.clear(companyId)
        setMessage('Reference cleared.')
      } else {
        await api.companies.normalization.set(companyId, streamId)
        setMessage('Reference set.')
      }
      await api.normalization.recalculate()
      setMessage('Reference set and normalization recalculated.')
      onCompanyUpdated?.()
      load()
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    } finally {
      setWorking(false)
    }
  }

  const recalcAll = async () => {
    setWorking(true)
    try {
      await api.normalization.recalculate()
      setMessage('Normalization recalculated.')
    } finally {
      setWorking(false)
    }
  }

  const currentRef = company?.normalize_stream_id
  const currentScale = company?.scaling_factor
  const currentSetpoint = company?.normalize_setpoint ?? 1.0
  const isManual = !!company?.scaling_factor_manual

  const saveSetpoint = async () => {
    const val = parseFloat(setpointInput)
    if (isNaN(val) || val <= 0) {
      setMessage('Setpoint must be a positive number.')
      return
    }
    setWorking(true)
    try {
      await api.companies.normalization.setSetpoint(companyId, val)
      setMessage(`Setpoint updated to ${val.toFixed(3)} and normalization recalculated.`)
      onCompanyUpdated?.()
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    } finally {
      setWorking(false)
      setEditingSetpoint(false)
    }
  }

  const saveCustomFactor = async () => {
    const val = parseFloat(customFactorInput)
    if (isNaN(val) || val <= 0) {
      setMessage('Scaling factor must be a positive number.')
      return
    }
    setWorking(true)
    try {
      await api.companies.normalization.setCustomFactor(companyId, val)
      setMessage(`Custom scaling factor set to ${val} and normalization recalculated.`)
      onCompanyUpdated?.()
      load()
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    } finally {
      setWorking(false)
      setEditingCustomFactor(false)
    }
  }

  const clearCustomFactor = async () => {
    setWorking(true)
    try {
      await api.companies.normalization.clearCustomFactor(companyId)
      setMessage('Custom scaling factor cleared.')
      onCompanyUpdated?.()
      load()
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    } finally {
      setWorking(false)
    }
  }

  return (
    <div>
      {/* Current state */}
      <div style={{
        background: colors.card, border: `1px solid ${colors.border}`,
        borderRadius: '6px', padding: '12px 14px', marginBottom: '16px',
      }}>
        <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.textSecondary, marginBottom: '4px' }}>
          Reference stream
        </div>
        <div style={{ fontFamily: FONT, fontSize: '12px', color: isManual ? colors.textDim : (currentRef ? colors.textPrimary : colors.textDim) }}>
          {isManual ? '(disabled — custom factor active)' : (currentRef || '(none)')}
        </div>
        {currentScale != null && (
          <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            scaling_factor = {currentScale.toFixed(6)}
            {isManual && (
              <span style={{
                fontFamily: FONT, fontSize: '10px', color: colors.accent,
                border: `1px solid ${colors.accent}`, borderRadius: '3px', padding: '1px 5px',
              }}>manual</span>
            )}
          </div>
        )}

        {/* Custom factor editor */}
        <div style={{ marginTop: '10px', borderTop: `1px solid ${colors.border}`, paddingTop: '10px' }}>
          <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.textSecondary, marginBottom: '6px' }}>
            Custom scaling factor
          </div>
          {editingCustomFactor ? (
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <input
                type="number"
                value={customFactorInput}
                onChange={e => setCustomFactorInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') saveCustomFactor(); if (e.key === 'Escape') setEditingCustomFactor(false) }}
                autoFocus
                style={{
                  fontFamily: FONT, fontSize: '12px', width: '120px',
                  background: colors.hover, border: `1px solid ${colors.accent}`,
                  color: colors.textPrimary, borderRadius: '4px', padding: '3px 7px',
                }}
              />
              <button onClick={saveCustomFactor} disabled={working} style={{
                fontFamily: FONT, fontSize: '11px', padding: '3px 8px',
                background: colors.accent + '22', border: `1px solid ${colors.accent}`,
                color: colors.accent, borderRadius: '4px', cursor: 'pointer',
              }}>Save</button>
              <button onClick={() => setEditingCustomFactor(false)} style={{
                fontFamily: FONT, fontSize: '11px', padding: '3px 8px',
                background: 'transparent', border: `1px solid ${colors.border}`,
                color: colors.textDim, borderRadius: '4px', cursor: 'pointer',
              }}>Cancel</button>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <span style={{ fontFamily: FONT, fontSize: '12px', color: isManual ? colors.textPrimary : colors.textDim }}>
                {isManual ? currentScale?.toFixed(6) : '(not set)'}
              </span>
              <button onClick={() => { setCustomFactorInput(isManual ? (currentScale ?? '').toString() : ''); setEditingCustomFactor(true) }} style={{
                fontFamily: FONT, fontSize: '10px', padding: '2px 7px',
                background: 'transparent', border: `1px solid ${colors.border}`,
                color: colors.textDim, borderRadius: '3px', cursor: 'pointer',
              }}>Set</button>
              {isManual && (
                <button onClick={clearCustomFactor} disabled={working} style={{
                  fontFamily: FONT, fontSize: '10px', padding: '2px 7px',
                  background: 'transparent', border: `1px solid ${colors.border}`,
                  color: colors.textDim, borderRadius: '3px', cursor: 'pointer',
                }}>Clear</button>
              )}
            </div>
          )}
        </div>

        {/* Setpoint editor */}
        <div style={{ marginTop: '10px', borderTop: `1px solid ${colors.border}`, paddingTop: '10px' }}>
          <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.textSecondary, marginBottom: '6px' }}>
            Setpoint
          </div>
          {editingSetpoint ? (
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <input
                type="number"
                value={setpointInput}
                onChange={e => setSetpointInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') saveSetpoint(); if (e.key === 'Escape') setEditingSetpoint(false) }}
                autoFocus
                style={{
                  fontFamily: FONT, fontSize: '12px', width: '100px',
                  background: colors.hover, border: `1px solid ${colors.accent}`,
                  color: colors.textPrimary, borderRadius: '4px', padding: '3px 7px',
                }}
              />
              <button onClick={saveSetpoint} disabled={working} style={{
                fontFamily: FONT, fontSize: '11px', padding: '3px 8px',
                background: colors.accent + '22', border: `1px solid ${colors.accent}`,
                color: colors.accent, borderRadius: '4px', cursor: 'pointer',
              }}>Save</button>
              <button onClick={() => setEditingSetpoint(false)} style={{
                fontFamily: FONT, fontSize: '11px', padding: '3px 8px',
                background: 'transparent', border: `1px solid ${colors.border}`,
                color: colors.textDim, borderRadius: '4px', cursor: 'pointer',
              }}>Cancel</button>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <span style={{ fontFamily: FONT, fontSize: '12px', color: colors.textPrimary }}>
                {currentSetpoint.toFixed(3)}
              </span>
              <button onClick={() => { setSetpointInput(currentSetpoint.toFixed(3)); setEditingSetpoint(true) }} disabled={isManual} style={{
                fontFamily: FONT, fontSize: '10px', padding: '2px 7px',
                background: 'transparent', border: `1px solid ${colors.border}`,
                color: isManual ? colors.textDim + '55' : colors.textDim,
                borderRadius: '3px', cursor: isManual ? 'default' : 'pointer',
                opacity: isManual ? 0.4 : 1,
              }}>Edit</button>
            </div>
          )}
        </div>
      </div>

      {/* Stream picker */}
      {isManual ? (
        <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, marginBottom: '16px', padding: '8px 10px', background: colors.hover, borderRadius: '4px', border: `1px solid ${colors.border}` }}>
          Stream selection disabled — custom scaling factor active.
        </div>
      ) : (
        <>
          <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, marginBottom: '8px' }}>
            Select a reference stream (input or output, flow &gt; 0). Clicking the current reference clears it.
          </div>

          {loading ? (
            <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>Loading…</div>
          ) : candidates.length === 0 ? (
            <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>No eligible streams.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '16px' }}>
              {candidates.map(c => (
                <button
                  key={c.stream_id}
                  disabled={working}
                  onClick={() => setRef(c.stream_id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '7px 10px', borderRadius: '4px', cursor: 'pointer',
                    background: c.is_current ? colors.accent + '22' : colors.hover,
                    border: `1px solid ${c.is_current ? colors.accent : colors.border}`,
                    textAlign: 'left', width: '100%',
                  }}
                >
                  <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim, minWidth: '42px' }}>{c.stream_id}</span>
                  <span style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, minWidth: '30px' }}>[{c.direction === 'input' ? 'in' : 'out'}]</span>
                  <span style={{ fontFamily: FONT, fontSize: '12px', color: colors.textPrimary, flex: 1 }}>{c.stream_name}</span>
                  <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textSecondary }}>
                    {c.flow_kton_per_year.toFixed(3)} kt/yr
                  </span>
                  {c.is_current && <span style={{ fontFamily: FONT, fontSize: '10px', color: colors.accent }}>★ current</span>}
                </button>
              ))}
            </div>
          )}
        </>
      )}

      <button
        onClick={recalcAll}
        disabled={working}
        style={{
          fontFamily: FONT, fontSize: '11px', padding: '5px 12px',
          background: colors.hover, border: `1px solid ${colors.border}`,
          color: colors.textSecondary, borderRadius: '4px', cursor: 'pointer',
        }}
      >
        Recalculate All
      </button>

      {message && (
        <div style={{ fontFamily: FONT, fontSize: '11px', color: colors.scoreHigh, marginTop: '10px' }}>
          {message}
        </div>
      )}
    </div>
  )
}
