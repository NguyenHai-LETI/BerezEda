'use client'

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'
import { Locale, DEFAULT_LOCALE, storeLocale, detectInitialLocale } from '@/lib/i18n'

import ru from '@/messages/ru.json'
import en from '@/messages/en.json'
import vi from '@/messages/vi.json'

const ALL_MESSAGES = { ru, en, vi } as const

function getNestedValue(obj: Record<string, any>, key: string): string {
  const value = key.split('.').reduce((acc: any, part) => {
    return acc && typeof acc === 'object' ? acc[part] : undefined
  }, obj)
  return typeof value === 'string' ? value : key
}

interface I18nContextValue {
  locale: Locale
  t: (key: string) => string
  setLocale: (locale: Locale) => void
}

const I18nContext = createContext<I18nContextValue>({
  locale: DEFAULT_LOCALE,
  t: (key) => key,
  setLocale: () => {},
})

export function useI18n() {
  return useContext(I18nContext)
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE)

  useEffect(() => {
    const initial = detectInitialLocale()
    setLocaleState(initial)
    // Persist auto-detected locale to cookie so next visit keeps same language
    storeLocale(initial)
    document.documentElement.lang = initial
  }, [])

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale)
    storeLocale(newLocale)
    document.documentElement.lang = newLocale
  }, [])

  const t = useCallback((key: string): string => {
    return getNestedValue(ALL_MESSAGES[locale] as Record<string, any>, key)
  }, [locale])

  return (
    <I18nContext.Provider value={{ locale, t, setLocale }}>
      {children}
    </I18nContext.Provider>
  )
}
