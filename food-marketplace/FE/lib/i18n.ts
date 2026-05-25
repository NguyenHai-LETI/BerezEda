export const LOCALES = ['ru', 'en', 'vi'] as const
export type Locale = (typeof LOCALES)[number]
export const DEFAULT_LOCALE: Locale = 'ru'

export const LOCALE_NAMES: Record<Locale, string> = {
  ru: 'Русский',
  en: 'English',
  vi: 'Tiếng Việt',
}

const LOCALE_COOKIE = 'locale'

export function getStoredLocale(): Locale {
  if (typeof document === 'undefined') return DEFAULT_LOCALE
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${LOCALE_COOKIE}=([^;]*)`))
  const val = match?.[1]
  return val && (LOCALES as readonly string[]).includes(val) ? (val as Locale) : DEFAULT_LOCALE
}

export function storeLocale(locale: Locale) {
  if (typeof document === 'undefined') return
  document.cookie = `${LOCALE_COOKIE}=${locale};path=/;max-age=${60 * 60 * 24 * 365};SameSite=Lax`
}

export function detectInitialLocale(): Locale {
  // Cookie takes priority (explicit user preference)
  const hasCookie = typeof document !== 'undefined' && document.cookie.includes(`${LOCALE_COOKIE}=`)
  if (hasCookie) return getStoredLocale()

  // Auto-detect from browser language
  if (typeof navigator !== 'undefined') {
    const lang = navigator.language.toLowerCase()
    if (lang.startsWith('vi')) return 'vi'
    if (lang.startsWith('en')) return 'en'
    if (lang.startsWith('ru')) return 'ru'
  }
  return DEFAULT_LOCALE
}
