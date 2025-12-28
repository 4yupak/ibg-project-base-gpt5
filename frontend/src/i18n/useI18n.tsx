import { createContext, useContext, useState, useCallback, ReactNode, useMemo } from 'react'
import { translations, Language } from './translations'

export interface I18nContextType {
  lang: Language
  language: Language  // alias for lang
  setLang: (lang: Language) => void
  t: (key: string, params?: Record<string, string | number>) => string
  currency: string
  setCurrency: (currency: string) => void
  formatPrice: (price: number | null | undefined, options?: { showCurrency?: boolean }) => string
}

const I18nContext = createContext<I18nContextType | null>(null)

// Currency exchange rates (simplified - in production, fetch from API)
const exchangeRates: Record<string, number> = {
  USD: 1,
  THB: 35.5,
  IDR: 15800,
  EUR: 0.92,
  RUB: 92,
}

// Get nested value from object by dot-separated path
function getNestedValue(obj: Record<string, unknown>, path: string): string | undefined {
  const keys = path.split('.')
  let current: unknown = obj
  
  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = (current as Record<string, unknown>)[key]
    } else {
      return undefined
    }
  }
  
  return typeof current === 'string' ? current : undefined
}

// Replace {param} placeholders with values
function interpolate(template: string, params?: Record<string, string | number>): string {
  if (!params) return template
  
  return template.replace(/\{(\w+)\}/g, (match, key) => {
    return params[key] !== undefined ? String(params[key]) : match
  })
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(() => {
    // Try to get from localStorage or use browser language
    const stored = localStorage.getItem('propbase-lang') as Language | null
    if (stored && (stored === 'en' || stored === 'ru')) return stored
    
    const browserLang = navigator.language.slice(0, 2)
    return browserLang === 'ru' ? 'ru' : 'en'
  })
  
  const [currency, setCurrencyState] = useState(() => {
    return localStorage.getItem('propbase-currency') || 'USD'
  })
  
  const setLang = useCallback((newLang: Language) => {
    setLangState(newLang)
    localStorage.setItem('propbase-lang', newLang)
  }, [])
  
  const setCurrency = useCallback((newCurrency: string) => {
    setCurrencyState(newCurrency)
    localStorage.setItem('propbase-currency', newCurrency)
  }, [])
  
  const t = useCallback((key: string, params?: Record<string, string | number>): string => {
    const translation = getNestedValue(translations[lang] as Record<string, unknown>, key)
    
    if (!translation) {
      // Fallback to English
      const fallback = getNestedValue(translations.en as Record<string, unknown>, key)
      if (!fallback) {
        console.warn(`Missing translation: ${key}`)
        return key
      }
      return interpolate(fallback, params)
    }
    
    return interpolate(translation, params)
  }, [lang])
  
  const formatPrice = useCallback((
    price: number | null | undefined, 
    options?: { showCurrency?: boolean }
  ): string => {
    if (price === null || price === undefined) return 'N/A'
    
    const { showCurrency = true } = options || {}
    
    // Convert from USD to selected currency
    const rate = exchangeRates[currency] || 1
    const converted = price * rate
    
    // Format number
    const formatted = new Intl.NumberFormat(lang === 'ru' ? 'ru-RU' : 'en-US', {
      maximumFractionDigits: 0,
    }).format(converted)
    
    if (!showCurrency) return formatted
    
    // Add currency symbol
    const symbols: Record<string, string> = {
      USD: '$',
      THB: '฿',
      IDR: 'Rp',
      EUR: '€',
      RUB: '₽',
    }
    
    const symbol = symbols[currency] || currency
    
    return currency === 'USD' || currency === 'EUR' 
      ? `${symbol}${formatted}` 
      : `${formatted} ${symbol}`
  }, [currency, lang])
  
  const value = useMemo(() => ({
    lang,
    language: lang,  // alias for lang
    setLang,
    t,
    currency,
    setCurrency,
    formatPrice,
  }), [lang, setLang, t, currency, setCurrency, formatPrice])
  
  return (
    <I18nContext.Provider value={value}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n(): I18nContextType {
  const context = useContext(I18nContext)
  if (!context) {
    throw new Error('useI18n must be used within I18nProvider')
  }
  return context
}
