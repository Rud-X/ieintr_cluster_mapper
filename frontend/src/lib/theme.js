export const COLORS = {
  bg: '#0f1117',
  card: '#181b23',
  hover: '#1e2230',
  border: '#2a2e3a',
  textPrimary: '#e8eaed',
  textSecondary: '#9aa0ad',
  textDim: '#5f6577',
  accent: '#5B9BD5',
  scoreHigh: '#4ade80',
  scoreMid: '#facc15',
  scoreLow: '#fb923c',
  scorePoor: '#f87171',
}

export const COMPANY_COLORS = [
  '#E8915A', '#5B9BD5', '#7BC67E', '#D4A0D9',
  '#E06C75', '#C9B458', '#6CC1C8', '#F28B82',
  '#A4C9A4', '#B8A9C9', '#D4956B', '#8BB8D0',
]

export const FONT = "'JetBrains Mono', monospace"

export const STATUS_COLORS = {
  candidate: '#C9B458',
  confirmed: '#4ade80',
  rejected: '#f87171',
}

export const NODE_TYPE_COLORS = {
  company: COLORS.accent,
  import_source: '#7BC67E',
  export_sink: '#D4A0D9',
  waste_facility: '#fb923c',
}

export const STREAM_TYPE_COLORS = {
  raw_material: '#5B9BD5',  // feedstock — blue
  products:     '#A78BFA',  // product — purple
  waste:        '#9aa0ad',  // waste — grey
  default:      '#5f6577',  // unknown — dim
}
