'use client'
import { useEffect, useState, useRef } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { getUser, logout } from '@/lib/auth'
import Link from 'next/link'
import { Home, Package, LogOut, ChevronDown, Settings, Globe, PanelLeft } from 'lucide-react'
import { useI18n } from '@/contexts/I18nContext'
import { LOCALES, LOCALE_NAMES, type Locale } from '@/lib/i18n'
import { cn } from '@/lib/utils'

export default function LockerOwnerLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { t, locale, setLocale } = useI18n()
  const [ready, setReady] = useState(false)
  const [user, setUser] = useState<ReturnType<typeof getUser>>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const u = getUser()
    if (!u) { router.replace('/login'); return }
    if (u.role !== 'owner_locker' && u.role !== 'admin') {
      router.replace('/')
      return
    }
    setUser(u)
    setReady(true)
  }, [])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  if (!ready) return (
    <div className="flex items-center justify-center h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"/>
    </div>
  )

  const initials = user?.name
    ? user.name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() ?? 'L'

  const NAV = [
    { href: '/locker-owner', label: t('locker_owner.nav.home'), icon: Home },
    { href: '/locker-owner/lockers', label: t('locker_owner.nav.my_lockers'), icon: Package },
  ]

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className={`hidden md:flex flex-col bg-surface border-r border-divider fixed h-full z-10 overflow-hidden transition-all duration-200 ${collapsed ? 'w-[72px]' : 'w-64'}`}>
        <div className={`flex items-center border-b border-divider py-5 ${collapsed ? 'px-3 justify-center flex-wrap gap-y-2' : 'px-5 gap-3'}`}>
          <div className="w-9 h-9 rounded-[10px] bg-primary flex items-center justify-center text-ink-100 font-extrabold text-base shrink-0">Б</div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-gray-900 leading-tight">БережЕда</p>
              <p className="text-xs text-gray-400 font-medium uppercase tracking-wider mt-0.5">{t('locker_owner.role')}</p>
            </div>
          )}
          <button
            onClick={() => setCollapsed(c => !c)}
            title={collapsed ? 'Развернуть' : 'Свернуть'}
            className="p-1.5 rounded-[8px] text-ink-40 hover:text-ink-100 hover:bg-line transition-colors shrink-0"
          >
            <PanelLeft className={`h-4 w-4 transition-transform duration-200 ${collapsed ? 'rotate-180' : ''}`} />
          </button>
        </div>
        <nav className={`flex-1 py-3 overflow-y-auto space-y-0.5 ${collapsed ? 'px-2' : 'p-4'}`} aria-label="Sidebar navigation">
          <ul className="space-y-1">
            {NAV.map(item => {
              const Icon = item.icon
              const isActive = pathname === item.href
              return (
                <li key={item.href}>
                  <Link href={item.href}
                    title={collapsed ? item.label : undefined}
                    className={`flex items-center gap-3 px-3 py-3 rounded-md transition-colors ${collapsed ? 'justify-center' : ''} ${
                      isActive ? 'bg-primary/10 text-primary font-medium' : 'text-text hover:bg-divider'
                    }`}>
                    <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                    {!collapsed && <span>{item.label}</span>}
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>
      </aside>

      {/* Main */}
      <div className={`flex-1 flex flex-col transition-[margin] duration-200 ${collapsed ? 'md:ml-[72px]' : 'md:ml-64'}`}>
        {/* Topbar */}
        <header className="hidden md:flex items-center justify-end gap-2 px-6 h-14 bg-surface border-b border-divider sticky top-0 z-10">
          <div ref={dropdownRef} className="relative">
            <button
              onClick={() => setDropdownOpen(prev => !prev)}
              className="flex items-center gap-2 pl-1.5 pr-3 py-1.5 rounded-full hover:bg-gray-100 transition-colors border border-transparent hover:border-gray-200"
            >
              <div className="w-7 h-7 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs font-bold shrink-0">
                {initials}
              </div>
              <span className="text-sm font-semibold text-gray-900">{user?.name ?? t('locker_owner.default_name')}</span>
              <ChevronDown className={`h-3.5 w-3.5 text-gray-400 transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden z-50">
                {/* User info */}
                <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-bold shrink-0">
                    {initials}
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-gray-900 truncate">{user?.name ?? t('locker_owner.default_name')}</div>
                    <div className="text-xs text-gray-400 truncate">{user?.email ?? ''}</div>
                  </div>
                </div>

                {/* Menu */}
                <div className="py-1">
                  <Link
                    href="/locker-owner/lockers"
                    onClick={() => setDropdownOpen(false)}
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <Settings className="h-4 w-4 text-gray-400 shrink-0" />
                    {t('locker_owner.dropdown.my_lockers')}
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
                <div className="border-t border-gray-100 py-1">
                  <button
                    onClick={() => { logout(); router.replace('/login') }}
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 transition-colors w-full"
                  >
                    <LogOut className="h-4 w-4 shrink-0" />
                    {t('header.logout')}
                  </button>
                </div>
              </div>
            )}
          </div>
        </header>

        <main className="flex-1 pb-20 md:pb-0">
          {children}
        </main>
      </div>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-surface border-t border-divider z-50" aria-label="Bottom navigation">
        <div className="flex items-center justify-around h-14 sm:h-16 px-1 sm:px-2">
          {NAV.map(item => {
            const Icon = item.icon
            const isActive = pathname === item.href
            return (
              <Link key={item.href} href={item.href}
                className={`flex flex-col items-center justify-center flex-1 h-full transition-colors rounded-md py-1 ${
                  isActive ? 'text-primary' : 'text-muted'
                }`}
                aria-label={item.label}>
                <Icon className="h-4 w-4 sm:h-5 sm:w-5 mb-0.5 sm:mb-1" aria-hidden="true" />
                <span className="text-[10px] sm:text-xs leading-tight">{item.label}</span>
              </Link>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
