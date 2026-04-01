import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import { DirectionBadge } from '../shared/Badge'
import SortableHeader from '../shared/SortableHeader'
import { api } from '../../lib/api'

function useSorted(items, defaultField = 'stream_id') {
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

export default function StreamsTable({ onlyIncluded = false, includedIds = new Set() }) {
  const { colors } = useTheme()
  const navigate = useNavigate()
  const params = useParams()
  const selectedId = params['*']?.split('/')[0] || null
  const [streams, setStreams] = useState([])
  const [loading, setLoading] = useState(true)
  const { sorted, sortField, sortDir, onSort } = useSorted(streams)

  const [filters, setFilters] = useState({})
  const sf = (field, val) => setFilters(prev => ({ ...prev, [field]: val }))
  const filtered = applyFilters(sorted, filters)
  const displayed = onlyIncluded ? filtered.filter(s => includedIds.has(s.company_id)) : filtered

  useEffect(() => {
    api.streams.list().then(setStreams).finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ padding: '20px' }}>
      {[...Array(6)].map((_, i) => (
        <div key={i} className="pulse" style={{ height: '32px', background: colors.card, borderRadius: '4px', marginBottom: '4px', opacity: 1 - i * 0.1 }} />
      ))}
    </div>
  )

  const sh = (label, field, align) => <SortableHeader label={label} field={field} sortField={sortField} sortDir={sortDir} onSort={onSort} align={align} />

  const dirOpts = [{ value: 'input', label: 'Input' }, { value: 'output', label: 'Output' }]
  const typeOpts = [
    { value: 'raw_material', label: 'Raw material' },
    { value: 'products', label: 'Products' },
    { value: 'waste', label: 'Waste' },
  ]

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {sh('ID', 'stream_id')}
            {sh('Company', 'company_name')}
            {sh('Name', 'stream_name')}
            {sh('Dir', 'direction')}
            {sh('Type', 'stream_type')}
            {sh('kt/yr', 'flow_kton_per_year', 'right')}
            {sh('C%', 'carbon_pct', 'right')}
          </tr>
          <tr>
            <FI field="stream_id" filters={filters} sf={sf} />
            <FI field="company_name" filters={filters} sf={sf} />
            <FI field="stream_name" filters={filters} sf={sf} />
            <FI field="direction" filters={filters} sf={sf} type="select" options={dirOpts} />
            <FI field="stream_type" filters={filters} sf={sf} type="select" options={typeOpts} />
            <FI field="flow_kton_per_year" filters={filters} sf={sf} />
            <FI field="carbon_pct" filters={filters} sf={sf} />
          </tr>
        </thead>
        <tbody>
          {displayed.map(s => {
            const isSelected = s.stream_id === selectedId
            const missingCarbon = s.carbon_pct == null || s.carbon_pct_complete === 0
            const rowBg = isSelected ? colors.hover : missingCarbon ? colors.scorePoor + '14' : 'transparent'
            const hoverBg = missingCarbon ? colors.scorePoor + '28' : colors.hover + '88'
            return (
              <tr key={s.stream_id}
                onClick={() => navigate(`/streams/${s.stream_id}`)}
                style={{ background: rowBg, cursor: 'pointer' }}
                onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = hoverBg }}
                onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = rowBg }}
              >
                <TD dim>{s.stream_id}</TD>
                <TD dim>{s.company_name}</TD>
                <TD>{s.stream_name}</TD>
                <TD><DirectionBadge direction={s.direction} /></TD>
                <TD dim>{s.stream_type || '—'}</TD>
                <TD align="right" dim>{s.flow_kton_per_year?.toFixed(3) ?? '—'}</TD>
                <TD align="right" dim>
                  {s.carbon_pct != null
                    ? `${(s.carbon_pct * 100).toFixed(1)}%${s.carbon_pct_complete === 0 ? '*' : ''}`
                    : '—'}
                </TD>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
