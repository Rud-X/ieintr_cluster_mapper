import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { NodeTypeBadge } from '../shared/Badge'
import ToggleSwitch from '../shared/ToggleSwitch'
import SortableHeader from '../shared/SortableHeader'

function useSorted(items, defaultField = 'company_id') {
  const [sortField, setSortField] = useState(defaultField)
  const [sortDir, setSortDir] = useState('asc')

  const onSort = (field) => {
    if (field === sortField) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortDir('asc') }
  }

  const sorted = [...items].sort((a, b) => {
    let av = a[sortField], bv = b[sortField]
    if (av == null) av = sortDir === 'asc' ? Infinity : -Infinity
    if (bv == null) bv = sortDir === 'asc' ? Infinity : -Infinity
    if (typeof av === 'string') return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
    return sortDir === 'asc' ? av - bv : bv - av
  })

  return { sorted, sortField, sortDir, onSort }
}

function TD({ children, align = 'left', dim }) {
  const { colors } = useTheme()
  return (
    <td style={{
      padding: '7px 12px',
      fontFamily: FONT,
      fontSize: '12px',
      color: dim ? colors.textDim : colors.textPrimary,
      textAlign: align,
      borderBottom: `1px solid ${colors.border}`,
      whiteSpace: 'nowrap',
    }}>
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

export default function CompaniesTable({ companies, loading, error, toggleIncluded, onlyIncluded, includedIds }) {
  const { colors } = useTheme()
  const navigate = useNavigate()
  const params = useParams()
  const selectedId = params['*']?.split('/')[0] || null

  const { sorted, sortField, sortDir, onSort } = useSorted(companies)
  const selectedRowRef = useRef(null)

  const [filters, setFilters] = useState({})
  const sf = (field, val) => setFilters(prev => ({ ...prev, [field]: val }))
  const filtered = applyFilters(sorted, filters)
  const displayed = onlyIncluded ? filtered.filter(c => includedIds.has(c.company_id)) : filtered

  useEffect(() => {
    if (selectedRowRef.current) {
      selectedRowRef.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [selectedId, loading])

  if (loading) return (
    <div style={{ padding: '20px' }}>
      {[...Array(8)].map((_, i) => (
        <div key={i} className="pulse" style={{
          height: '32px', background: colors.card, borderRadius: '4px',
          marginBottom: '4px', opacity: 1 - i * 0.08,
        }} />
      ))}
    </div>
  )
  if (error) return <div style={{ padding: '20px', color: colors.scorePoor, fontFamily: FONT, fontSize: '12px' }}>Error: {error}</div>

  const sh = (label, field, align) => (
    <SortableHeader label={label} field={field} sortField={sortField} sortDir={sortDir} onSort={onSort} align={align} />
  )

  const nodeTypeOpts = [
    { value: 'company', label: 'Company' },
    { value: 'import_source', label: 'IMP' },
    { value: 'export_sink', label: 'EXP' },
    { value: 'waste_facility', label: 'WMF' },
  ]
  const yesNoOpts = [{ value: '1', label: 'Yes' }, { value: '0', label: 'No' }]

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {sh('Type', 'node_type')}
            {sh('ID', 'company_id')}
            {sh('Name', 'name')}
            {sh('Sector', 'sector')}
            {sh('Inc', 'included', 'center')}
            {sh('#Streams', 'stream_count', 'right')}
            {sh('#Flows', 'flow_count', 'right')}
            {sh('#Connected', 'streams_in_flows', 'right')}
          </tr>
          <tr>
            <FI field="node_type" filters={filters} sf={sf} type="select" options={nodeTypeOpts} />
            <FI field="company_id" filters={filters} sf={sf} />
            <FI field="name" filters={filters} sf={sf} />
            <FI field="sector" filters={filters} sf={sf} />
            <FI field="included" filters={filters} sf={sf} type="select" options={yesNoOpts} />
            <FI field="stream_count" filters={filters} sf={sf} />
            <FI field="flow_count" filters={filters} sf={sf} />
            <FI field="streams_in_flows" filters={filters} sf={sf} />
          </tr>
        </thead>
        <tbody>
          {displayed.map(company => {
            const isSelected = company.company_id === selectedId
            return (
              <tr
                key={company.company_id}
                ref={isSelected ? selectedRowRef : null}
                onClick={() => navigate(`/companies/${company.company_id}`)}
                style={{
                  background: isSelected ? colors.hover : 'transparent',
                  cursor: 'pointer',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = colors.hover + '88' }}
                onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent' }}
              >
                <TD>
                  <NodeTypeBadge nodeType={company.node_type} />
                </TD>
                <TD dim>{company.company_id}</TD>
                <TD>
                  {isSelected && (
                    <span style={{ color: colors.accent, marginRight: '6px' }}>▶</span>
                  )}
                  {company.name}
                </TD>
                <TD dim>{company.sector || '—'}</TD>
                <TD align="center">
                  <div style={{ display: 'flex', justifyContent: 'center' }} onClick={e => e.stopPropagation()}>
                    <ToggleSwitch
                      checked={!!company.included}
                      onChange={() => toggleIncluded(company.company_id, company.included)}
                    />
                  </div>
                </TD>
                <TD align="right" dim>{company.stream_count ?? 0}</TD>
                <TD align="right" dim>{company.flow_count ?? 0}</TD>
                <TD align="right" dim>{company.streams_in_flows ?? 0}</TD>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
