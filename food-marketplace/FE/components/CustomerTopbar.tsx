'use client'

import { usePathname, useRouter } from 'next/navigation'
import { ChevronLeft, ChevronDown, User, Settings, CreditCard, HelpCircle, LogOut, Globe } from 'lucide-react'
import Link from 'next/link'
import { getUser, logout } from '@/lib/auth'
import { getNotifications } from '@/lib/api'
import { useEffect, useState, useRef } from 'react'
import { cn } from '@/lib/utils'
import { useI18n } from '@/contexts/I18nContext'
import { LOCALES, LOCALE_NAMES, type Locale } from '@/lib/i18n'

// Pathname → translation key
const PAGE_KEY_MAP: Record<string, string> = {
  '/':                     'pages.home',
  '/history':              'pages.history',
  '/map':                  'pages.map',
  '/favorites':            'pages.favorites',
  '/mypage':               'pages.profile',
  '/mypage/notifications': 'pages.notifications',
  '/mypage/account':       'pages.account',
  '/mypage/reviews':       'pages.my_reviews',
  '/mypage/payment':       'pages.payment',
  '/mypage/privacy':       'pages.privacy',
  '/mypage/terms':         'pages.terms',
  '/mypage/contact':       'pages.contact',
  '/mypage/language':      'pages.language',
  '/payment/select':       'pages.checkout',
  '/reviews/new':          'pages.new_review',
}

function derivePageKey(pathname: string): string | null {
  if (PAGE_KEY_MAP[pathname]) return PAGE_KEY_MAP[pathname]
  if (pathname.startsWith('/combos/') || pathname.startsWith('/items/')) return 'pages.combo'
  if (pathname.startsWith('/history/')) return 'pages.order'
  if (pathname.startsWith('/shops/')) return 'pages.shop'
  return null
}

// Returns [parentKey, currentKey] or null for root
const BREADCRUMB_KEYS: Record<string, [string, string]> = {
  '/history':              ['pages.home',    'pages.history'],
  '/map':                  ['pages.home',    'pages.map'],
  '/favorites':            ['pages.home',    'pages.favorites'],
  '/mypage':               ['pages.home',    'pages.profile'],
  '/mypage/notifications': ['pages.profile', 'pages.notifications'],
  '/mypage/account':       ['pages.profile', 'pages.account'],
  '/mypage/reviews':       ['pages.profile', 'pages.my_reviews'],
  '/mypage/payment':       ['pages.profile', 'pages.payment'],
  '/mypage/privacy':       ['pages.profile', 'pages.privacy'],
  '/mypage/terms':         ['pages.profile', 'pages.terms'],
  '/mypage/contact':       ['pages.profile', 'pages.contact'],
  '/mypage/language':      ['pages.profile', 'pages.language'],
  '/payment/select':       ['pages.home',    'pages.checkout'],
  '/reviews/new':          ['pages.my_reviews', 'pages.new_review'],
}

function deriveBreadcrumb(pathname: string, t: (k: string) => string): string[] | null {
  if (pathname === '/') return null
  const keys = BREADCRUMB_KEYS[pathname]
  if (keys) return keys.map(t)
  if (pathname.startsWith('/combos/') || pathname.startsWith('/items/')) return [t('pages.home'), t('pages.combo')]
  if (pathname.startsWith('/shops/')) return [t('pages.home'), t('pages.shop')]
  if (pathname.startsWith('/history/')) return [t('pages.history'), t('pages.order')]
  return null
}

export function CustomerTopbar() {
  const pathname = usePathname()
  const router = useRouter()
  const user = getUser()
  const { t, locale, setLocale } = useI18n()
  const [unread, setUnread] = useState(0)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getNotifications()
      .then((r: any) => {
        const list: any[] = r?.data || []
        setUnread(list.filter((n: any) => !n.is_read).length)
      })
      .catch(() => {})
  }, [pathname])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function handleLogout() {
    logout()
    router.replace('/login')
  }

  const pageKey = derivePageKey(pathname)
  const title = pageKey ? t(pageKey) : ''
  const breadcrumb = deriveBreadcrumb(pathname, t)
  const hasBack = breadcrumb && breadcrumb.length > 1

  const initials = user?.name
    ? user.name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() ?? '?'

  return (
    <header className="sticky top-0 z-30 bg-surface/90 backdrop-blur-sm border-b border-line px-6 h-[60px] flex items-center justify-between gap-4">
      {/* Left */}
      <div className="flex flex-col justify-center min-w-0">
        {breadcrumb && (
          <div className="flex items-center gap-1 text-[11px] text-ink-40 mb-0.5">
            {hasBack && (
              <button
                onClick={() => router.back()}
                className="flex items-center gap-0.5 hover:text-ink-100 transition-colors mr-1"
              >
                <ChevronLeft className="h-3 w-3" />
                <span>{t('header.back')}</span>
              </button>
            )}
            {breadcrumb.map((c, i) => (
              <span key={i} className="flex items-center gap-1">
                {i > 0 && <span className="text-line2">/</span>}
                <span className={i === breadcrumb.length - 1 ? 'text-ink-60 font-medium' : ''}>{c}</span>
              </span>
            ))}
          </div>
        )}
        {title && (
          <h1 className="text-base font-bold text-ink-100 leading-tight truncate">{title}</h1>
        )}
      </div>

      {/* Right */}
      <div className="flex items-center gap-1 shrink-0">
        <div className="w-px h-6 bg-line mx-1" />

        {/* User dropdown */}
        <div ref={dropdownRef} className="relative">
          <button
            onClick={() => setDropdownOpen(prev => !prev)}
            className="flex items-center gap-2 pl-1.5 pr-2.5 py-1.5 rounded-full hover:bg-line/60 transition-colors border border-transparent hover:border-line"
          >
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-eco to-[#4CAF85] flex items-center justify-center text-white text-xs font-bold shrink-0">
              {initials}
            </div>
            <span className="hidden sm:block text-sm font-semibold text-ink-100">{user?.name ?? t('nav.profile')}</span>
            <ChevronDown className={cn('h-3.5 w-3.5 text-ink-60 transition-transform duration-200', dropdownOpen && 'rotate-180')} />
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 top-full mt-2 w-60 bg-surface rounded-[14px] shadow-lg border border-line overflow-hidden z-50">
              {/* User info */}
              <div className="px-4 py-3 border-b border-line flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-eco to-[#4CAF85] flex items-center justify-center text-white text-sm font-bold shrink-0">
                  {initials}
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-ink-100 truncate">{user?.name ?? t('nav.profile')}</div>
                  <div className="text-[11px] text-ink-40 truncate">{user?.email ?? ''}</div>
                </div>
              </div>

              {/* Nav items */}
              <div className="py-1">
                <Link href="/mypage" onClick={() => setDropdownOpen(false)}
                  className="flex items-center gap-3 px-4 py-2.5 text-sm text-ink-100 hover:bg-line/60 transition-colors">
                  <User className="h-4 w-4 text-ink-60 shrink-0" />
                  {t('header.my_profile')}
                </Link>
                <Link href="/mypage/account" onClick={() => setDropdownOpen(false)}
                  className="flex items-center gap-3 px-4 py-2.5 text-sm text-ink-100 hover:bg-line/60 transition-colors">
                  <Settings className="h-4 w-4 text-ink-60 shrink-0" />
                  {t('header.account_settings')}
                </Link>
                <Link href="/mypage/payment" onClick={() => setDropdownOpen(false)}
                  className="flex items-center gap-3 px-4 py-2.5 text-sm text-ink-100 hover:bg-line/60 transition-colors">
                  <CreditCard className="h-4 w-4 text-ink-60 shrink-0" />
                  {t('header.payment')}
                </Link>
                <Link href="/mypage/contact" onClick={() => setDropdownOpen(false)}
                  className="flex items-center gap-3 px-4 py-2.5 text-sm text-ink-100 hover:bg-line/60 transition-colors">
                  <HelpCircle className="h-4 w-4 text-ink-60 shrink-0" />
                  {t('header.support')}
                </Link>
              </div>

              {/* Language switcher */}
              <div className="border-t border-line px-4 py-3">
                <div className="flex items-center gap-2 mb-2">
                  <Globe className="h-4 w-4 text-ink-60 shrink-0" />
                  <span className="text-xs font-semibold text-ink-40 uppercase tracking-wide">{t('header.language')}</span>
                </div>
                <div className="flex gap-1.5">
                  {LOCALES.map(loc => (
                    <button
                      key={loc}
                      onClick={() => setLocale(loc as Locale)}
                      className={cn(
                        'flex-1 py-1.5 rounded-[8px] text-xs font-semibold transition-colors',
                        locale === loc
                          ? 'bg-primary text-ink-100'
                          : 'bg-line/60 text-ink-60 hover:bg-line hover:text-ink-100'
                      )}
                    >
                      {LOCALE_NAMES[loc as Locale]}
                    </button>
                  ))}
                </div>
              </div>

              {/* Logout */}
              <div className="border-t border-line py-1">
                <button onClick={handleLogout}
                  className="flex items-center gap-3 px-4 py-2.5 text-sm text-accent hover:bg-accent/10 transition-colors w-full">
                  <LogOut className="h-4 w-4 shrink-0" />
                  {t('header.logout')}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
