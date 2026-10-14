import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useMediaQuery } from '../hooks'

type Theme = 'light' | 'dark' | 'system'

interface ThemeContextType {
  theme: Theme
  resolvedTheme: 'light' | 'dark'
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window !== 'undefined') {
      try { const saved = localStorage.getItem('theme'); return saved === 'light' || saved === 'dark' ? saved : 'system' } catch { return 'system' }
    }
    return 'system'
  })
  const systemDark = useMediaQuery('(prefers-color-scheme: dark)')
  const resolvedTheme = theme === 'system' ? (systemDark ? 'dark' : 'light') : theme

  useEffect(() => {
    const root = window.document.documentElement
    root.classList.remove('light', 'dark')
    
    root.classList.add(resolvedTheme)
    try { localStorage.setItem('theme', theme) } catch { /* Theme still works when storage is unavailable. */ }
  }, [theme, resolvedTheme])

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
  }

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
