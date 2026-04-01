import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { FONT } from '../../lib/theme'
import { useTheme } from '../../lib/ThemeContext'
import SortableHeader from '../shared/SortableHeader'
import { api } from '../../lib/api'

function useSorted(items, defaultField = 'component_id') {
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

function Flag({ value, color }) {
  const { colors } = useTheme()
  if (!value) return <span style={{ color: colors.textDim }}>—</span>
  return <span style={{ color, fontWeight: '600', fontSize: '11px' }}>●</span>
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

export default function ComponentsTable() {
  const { colors } = useTheme()
  const navigate = useNavigate()
  const params = useParams()
  const selectedId = params['*']?.split('/')[0] || null
  const [components, setComponents] = useState([])
  const [loading, setLoading] = useState(true)
  const { sorted, sortField, sortDir, onSort } = useSorted(components)

  const [filters, setFilters] = useState({})
  const sf = (field, val) => setFilters(prev => ({ ...prev, [field]: val }))
  const filtered = applyFilters(sorted, filters)

  useEffect(() => {
    api.components.list().then(setComponents).finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ padding: '20px' }}>
      {[...Array(6)].map((_, i) => (
        <div key={i} className="pulse" style={{ height: '32px', background: colors.card, borderRadius: '4px', marginBottom: '4px', opacity: 1 - i * 0.1 }} />
      ))}
    </div>
  )

  const sh = (label, field, align) => <SortableHeader label={label} field={field} sortField={sortField} sortDir={sortDir} onSort={onSort} align={align} />

  const yesNoOpts = [{ value: '1', label: 'Yes' }, { value: '0', label: 'No' }]

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {sh('ID', 'component_id')}
            {sh('Name', 'name')}
            {sh('Category', 'category')}
            {sh('C%', 'carbon_weight_pct', 'right')}
            {sh('Manual', 'carbon_weight_pct_manual', 'center')}
            {sh('Review', 'needs_review', 'center')}
            {sh('Hazard', 'hazardous', 'center')}
          </tr>
          <tr>
            <FI field="component_id" filters={filters} sf={sf} />
            <FI field="name" filters={filters} sf={sf} />
            <FI field="category" filters={filters} sf={sf} />
            <FI field="carbon_weight_pct" filters={filters} sf={sf} />
            <FI field="carbon_weight_pct_manual" filters={filters} sf={sf} type="select" options={yesNoOpts} />
            <FI field="needs_review" filters={filters} sf={sf} type="select" options={yesNoOpts} />
            <FI field="hazardous" filters={filters} sf={sf} type="select" options={yesNoOpts} />
          </tr>
        </thead>
        <tbody>
          {filtered.map(c => {
            const isSelected = c.component_id === selectedId
            const missingCarbon = c.carbon_weight_pct == null
            const rowBg = isSelected ? colors.hover : missingCarbon ? colors.scorePoor + '14' : 'transparent'
            const hoverBg = missingCarbon ? colors.scorePoor + '28' : colors.hover + '88'
            return (
              <tr key={c.component_id}
                onClick={() => navigate(`/components/${c.component_id}`)}
                style={{ background: rowBg, cursor: 'pointer' }}
                onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = hoverBg }}
                onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = rowBg }}
              >
                <TD dim>{c.component_id}</TD>
                <TD>{c.name}</TD>
                <TD dim>{c.category || '—'}</TD>
                <TD align="right" dim>
                  {c.carbon_weight_pct != null
                    ? `${(c.carbon_weight_pct * 100).toFixed(2)}%`
                    : <span style={{ color: colors.scorePoor }}>—</span>}
                </TD>
                <TD align="center"><Flag value={c.carbon_weight_pct_manual} color={colors.scoreMid} /></TD>
                <TD align="center"><Flag value={c.needs_review} color={colors.scoreLow} /></TD>
                <TD align="center"><Flag value={c.hazardous} color={colors.scorePoor} /></TD>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
