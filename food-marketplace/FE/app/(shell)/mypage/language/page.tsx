'use client'

import { Globe, Check } from 'lucide-react'
import { useI18n } from '@/contexts/I18nContext'
import { LOCALES, LOCALE_NAMES, type Locale } from '@/lib/i18n'
import { cn } from '@/lib/utils'

export default function LanguagePage() {
  const { t, locale, setLocale } = useI18n()

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-5 max-w-[540px] mx-auto w-full">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-[10px] bg-primary-soft flex items-center justify-center shrink-0">
          <Globe className="h-5 w-5 text-ink-60" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-ink-100">{t('language.title')}</h2>
          <p className="text-sm text-ink-40">{t('language.subtitle')}</p>
        </div>
      </div>

      {/* Language list */}
      <section className="bg-surface rounded-card shadow-sm overflow-hidden">
        <div className="divide-y divide-line">
          {LOCALES.map(loc => {
            const isSelected = locale === loc
            return (
              <button
                key={loc}
                onClick={() => setLocale(loc as Locale)}
                className={cn(
                  'flex items-center gap-4 w-full px-5 py-4 text-left transition-colors',
                  isSelected ? 'bg-primary-soft' : 'hover:bg-bg/60'
                )}
              >
                {/* Language code badge */}
                <div className={cn(
                  'w-10 h-10 rounded-[10px] flex items-center justify-center text-sm font-bold shrink-0',
                  isSelected ? 'bg-primary text-ink-100' : 'bg-line/60 text-ink-60'
                )}>
                  {loc.toUpperCase()}
                </div>

                {/* Language name */}
                <div className="flex-1">
                  <div className={cn(
                    'text-sm font-semibold',
                    isSelected ? 'text-ink-100' : 'text-ink-100'
                  )}>
                    {LOCALE_NAMES[loc as Locale]}
                  </div>
                  <div className="text-xs text-ink-40 mt-0.5">
                    {t(`language.${loc}`)}
                  </div>
                </div>

                {/* Checkmark */}
                {isSelected && (
                  <Check className="h-5 w-5 text-eco shrink-0" />
                )}
              </button>
            )
          })}
        </div>
      </section>

      <p className="text-xs text-ink-40 text-center px-4">
        {locale === 'ru' && 'Язык применяется немедленно'}
        {locale === 'en' && 'Language is applied immediately'}
        {locale === 'vi' && 'Ngôn ngữ được áp dụng ngay lập tức'}
      </p>
    </div>
  )
}
