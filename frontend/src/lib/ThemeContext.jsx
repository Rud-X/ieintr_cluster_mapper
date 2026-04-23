import { createContext, useContext, useState, useEffect } from 'react'

export const DARK_COLORS = {
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

export const LIGHT_COLORS = {
  bg: '#ffffff',
  card: '#ffffff',
  hover: '#f0f2f5',
  border: '#d1d5db',
  textPrimary: '#111827',
  textSecondary: '#4b5563',
  textDim: '#9ca3af',
  accent: '#1d6db5',
  scoreHigh: '#16a34a',
  scoreMid: '#b45309',
  scoreLow: '#c2410c',
  scorePoor: '#dc2626',
}

const ThemeContext = createContext({
  theme: 'dark',
  colors: DARK_COLORS,
  toggleTheme: () => {},
})

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark')
  const colors = theme === 'dark' ? DARK_COLORS : LIGHT_COLORS

  useEffect(() => {
    document.body.style.background = colors.bg
    document.body.style.color = colors.textPrimary
    document.documentElement.style.setProperty('--scrollbar-thumb', colors.border)
    localStorage.setItem('theme', theme)
  }, [theme, colors])

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')

  return (
    <ThemeContext.Provider value={{ theme, colors, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  return useContext(ThemeContext)
}
