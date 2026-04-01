import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { useFlows } from '../../hooks/useFlows'
import { StatusBadge } from '../shared/Badge'
import SortableHeader from '../shared/SortableHeader'

function useSorted(items, defaultField = 'flow_id') {
  const [sortField, setSortField] = useState(defaultField)
  const [sortDir, setSortDir] = useState('asc')
  const onSort = (f) => {
    if (f === sortField) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortField(f); setSortDir('asc') }
  }
  const sorted = [...items].sort((a, b) => {
    let av = a[sortField] ?? '', bv = b[sortField] ?? ''
    if (typeof av === 'string') return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
    return sortDir === 'asc' ? av - bv : bv - av
  })
  return { sorted, sortField, sortDir, onSort }
}

function TD({ children, dim, align = 'left' }) {
  const { colors } = useTheme()
  return (
    <td style={{ padding: '7px 12px', fontFamily: FONT, fontSize: '12px', color: dim ? colors.textDim : colors.textPrimary, textAlign: align, borderBottom: `1px solid ${colors.border}`, whiteSpace: 'nowrap' }}>
      {children}
    </td>
  )
}

function FI({ field, filters, sf, type = 'text', options }) {
  const { colors } = useTheme()
  const fcell = {
    padding: '3px 12px 4px',
    background: colors.card,
    borderBottom: `1px solid ${colors.border}`,
    position: 'sticky',
    top: '34px',
    zIndex: 1,
  }
  const inp = {
    width: '100%', background: colors.bg, border: `1px solid ${colors.border}`,
    borderRadius: '3px', color: colors.textSecondary, fontFamily: FONT,
    fontSize: '10px', padding: '2px 5px', outline: 'none', boxSizing: 'border-box',
  }
  if (type === 'select') return (
    <th style={fcell}>
      <select value={filters[field] || 'all'} onChange={e => sf(field, e.target.value)}
        style={{ ...inp, cursor: 'pointer', appearance: 'none', paddingRight: '2px' }}>
        <option value="all">—</option>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </th>
  )
  return (
    <th style={fcell}>
      <input style={inp} value={filters[field] || ''} onChange={e => sf(field, e.target.value)} placeholder="…" />
    </th>
  )
}

function applyFilters(items, filters) {
  return items.filter(item =>
    Object.entries(filters).every(([k, v]) => {
      if (!v || v === 'all') return true
      const val = item[k]
      if (val == null) return false
      return String(val).toLowerCase().includes(v.toLowerCase())
    })
  )
}

export default function FlowsTable({ onlyIncluded = false, includedIds = new Set() }) {
  const { colors } = useTheme()
  const navigate = useNavigate()
  const params = useParams()
  const selectedId = params['*']?.split('/')[0] || null
  const { flows, loading, error } = useFlows()
  const { sorted, sortField, sortDir, onSort } = useSorted(flows)

  const [filters, setFilters] = useState({})
  const sf = (field, val) => setFilters(prev => ({ ...prev, [field]: val }))
  const filtered = applyFilters(sorted, filters)
  const displayed = onlyIncluded
    ? filtered.filter(f => includedIds.has(f.from_company_id) || includedIds.has(f.to_company_id))
    : filtered

  if (loading) return (
    <div style={{ padding: '20px' }}>
      {[...Array(6)].map((_, i) => (
        <div key={i} className="pulse" style={{ height: '32px', background: colors.card, borderRadius: '4px', marginBottom: '4px', opacity: 1 - i * 0.1 }} />
      ))}
    </div>
  )
  if (error) return <div style={{ padding: '20px', color: colors.scorePoor, fontFamily: FONT, fontSize: '12px' }}>Error: {error}</div>

  const sh = (label, field, align) => <SortableHeader label={label} field={field} sortField={sortField} sortDir={sortDir} onSort={onSort} align={align} />

  const statusOpts = [
    { value: 'candidate', label: 'Candidate' },
    { value: 'confirmed', label: 'Confirmed' },
    { value: 'rejected', label: 'Rejected' },
  ]

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {sh('ID', 'flow_id')}
            {sh('From', 'from_company_name')}
            {sh('Stream', 'from_stream_name')}
            {sh('To', 'to_company_name')}
            {sh('Stream', 'to_stream_name')}
            {sh('Type', 'flow_type')}
            {sh('Status', 'status')}
            {sh('kt/yr', 'flow_kton_per_year', 'right')}
          </tr>
          <tr>
            <FI field="flow_id" filters={filters} sf={sf} />
            <FI field="from_company_name" filters={filters} sf={sf} />
            <FI field="from_stream_name" filters={filters} sf={sf} />
            <FI field="to_company_name" filters={filters} sf={sf} />
            <FI field="to_stream_name" filters={filters} sf={sf} />
            <FI field="flow_type" filters={filters} sf={sf} />
            <FI field="status" filters={filters} sf={sf} type="select" options={statusOpts} />
            <FI field="flow_kton_per_year" filters={filters} sf={sf} />
          </tr>
        </thead>
        <tbody>
          {displayed.map(flow => {
            const isSelected = flow.flow_id === selectedId
            return (
              <tr key={flow.flow_id}
                onClick={() => navigate(`/flows/${flow.flow_id}`)}
                style={{ background: isSelected ? colors.hover : 'transparent', cursor: 'pointer' }}
                onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = colors.hover + '88' }}
                onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent' }}
              >
                <TD dim>{flow.flow_id}</TD>
                <TD>{flow.from_company_name}</TD>
                <TD dim>{flow.from_stream_name || '—'}</TD>
                <TD>{flow.to_company_name}</TD>
                <TD dim>{flow.to_stream_name || '—'}</TD>
                <TD dim>{flow.flow_type || '—'}</TD>
                <TD><StatusBadge status={flow.status} /></TD>
                <TD align="right" dim>{flow.flow_kton_per_year?.toFixed(3) ?? '—'}</TD>
              </tr>
            )
          })}
        </tbody>
      </table>
      {flows.length === 0 && (
        <div style={{ padding: '40px', textAlign: 'center', color: colors.textDim, fontFamily: FONT, fontSize: '12px' }}>
          No flows yet. Create flows from the Companies tab.
        </div>
      )}
    </div>
  )
}
