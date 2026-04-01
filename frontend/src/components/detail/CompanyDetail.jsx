import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { FONT, COMPANY_COLORS } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { useCompany } from '../../hooks/useCompanies'
import { NodeTypeBadge } from '../shared/Badge'
import ToggleSwitch from '../shared/ToggleSwitch'
import Tabs from '../shared/Tabs'
import StreamsTab from './StreamsTab'
import FlowsTab from './FlowsTab'
import NormalizationTab from './NormalizationTab'
import CreateFlowModal from './CreateFlowModal'
import { api } from '../../lib/api'

export default function CompanyDetail() {
  const { colors } = useTheme()
  const { id } = useParams()
  const { company, loading, error, reload, setCompany } = useCompany(id)
  const [tab, setTab] = useState('Streams')
  const [showCreateFlow, setShowCreateFlow] = useState(false)
  const [flowPrefill, setFlowPrefill] = useState(null)
  const [flowRefresh, setFlowRefresh] = useState(0)

  const toggleIncluded = async () => {
    const newVal = company.included ? 0 : 1
    setCompany(c => ({ ...c, included: newVal }))
    try {
      await api.companies.update(id, { included: newVal })
    } catch {
      setCompany(c => ({ ...c, included: company.included }))
    }
  }

  if (loading) return <div style={{ color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>Loading…</div>
  if (error) return <div style={{ color: colors.scorePoor, fontFamily: FONT, fontSize: '12px' }}>Error: {error}</div>
  if (!company) return null

  const colorIdx = parseInt(company.company_id.replace(/\D/g, ''), 10) - 1
  const companyColor = COMPANY_COLORS[colorIdx % COMPANY_COLORS.length]
  const isExternalNode = company.node_type !== 'company'
  const tabs = isExternalNode ? ['Streams', 'Flows'] : ['Streams', 'Flows', 'Normalization']

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Header card */}
      <div style={{
        background: colors.card, border: `1px solid ${colors.border}`,
        borderRadius: '6px', padding: '14px 16px', marginBottom: '16px',
        borderLeft: `3px solid ${companyColor}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <span style={{ fontFamily: FONT, fontSize: '15px', fontWeight: '600', color: colors.textPrimary, flex: 1 }}>
            {company.name}
          </span>
          <NodeTypeBadge nodeType={company.node_type} />
          <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim }}>{company.company_id}</span>
        </div>

        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '10px' }}>
          {[
            ['Sector', company.sector || '—'],
            ['Location', company.location || '—'],
            ['Streams', company.stream_count ?? 0],
            ['Flows', company.flow_count ?? 0],
          ].map(([label, value]) => (
            <div key={label}>
              <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '2px' }}>{label}</div>
              <div style={{ fontFamily: FONT, fontSize: '12px', color: colors.textSecondary }}>{value}</div>
            </div>
          ))}
          {company.normalize_stream_id && (
            <div>
              <div style={{ fontFamily: FONT, fontSize: '10px', color: colors.textDim, marginBottom: '2px' }}>Norm ref</div>
              <div style={{ fontFamily: FONT, fontSize: '12px', color: colors.textSecondary }}>{company.normalize_stream_id}</div>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontFamily: FONT, fontSize: '11px', color: colors.textDim }}>Included in analysis</span>
          <ToggleSwitch checked={!!company.included} onChange={toggleIncluded} />
        </div>
      </div>

      <Tabs tabs={tabs} active={tab} onChange={setTab} />

      {tab === 'Streams' && (
        <StreamsTab
          companyId={id}
          onCreateFlow={() => { setFlowPrefill(null); setShowCreateFlow(true) }}
          onCreateFlowFromStream={s => { setFlowPrefill({ fromStreamId: s.stream_id, fromCompanyId: id }); setShowCreateFlow(true) }}
        />
      )}
      {tab === 'Flows' && (
        <FlowsTab companyId={id} refresh={flowRefresh} />
      )}
      {tab === 'Normalization' && !isExternalNode && (
        <NormalizationTab companyId={id} company={company} onCompanyUpdated={reload} />
      )}

      {showCreateFlow && (
        <CreateFlowModal
          company={company}
          prefill={flowPrefill}
          onClose={() => { setShowCreateFlow(false); setFlowPrefill(null) }}
          onCreated={() => { setTab('Flows'); setFlowRefresh(r => r + 1) }}
        />
      )}
    </div>
  )
}
