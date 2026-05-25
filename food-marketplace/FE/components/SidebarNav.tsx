'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, History, MapPin, Heart, Bell, User, PanelLeft } from 'lucide-react'
import { routes } from '@/lib/routes'
import { cn } from '@/lib/utils'
import { getNotifications } from '@/lib/api'
import { useEffect, useState } from 'react'
import { useI18n } from '@/contexts/I18nContext'

interface Props {
  collapsed: boolean
  onToggle: () => void
}

export function SidebarNav({ collapsed, onToggle }: Props) {
  const pathname = usePathname()
  const [unread, setUnread] = useState(0)
  const { t } = useI18n()

  const navItems = [
    { id: 'home',      icon: Home,    labelKey: 'nav.home',          href: routes.home },
    { id: 'history',   icon: History, labelKey: 'nav.history',       href: routes.history },
    { id: 'map',       icon: MapPin,  labelKey: 'nav.map',           href: routes.map },
    { id: 'favorites', icon: Heart,   labelKey: 'nav.favorites',     href: routes.favorites },
    { id: 'notifs',    icon: Bell,    labelKey: 'nav.notifications',  href: routes.notifications },
    { id: 'mypage',    icon: User,    labelKey: 'nav.profile',       href: routes.myPage },
  ] as const

  useEffect(() => {
    getNotifications()
      .then((r: any) => {
        const list: any[] = r?.data || []
        setUnread(list.filter(n => !n.is_read).length)
      })
      .catch(() => {})
  }, [])

  return (
    <aside className={cn(
      'hidden lg:flex lg:flex-col fixed h-screen top-0 left-0 z-40 bg-surface border-r border-line transition-all duration-200 overflow-hidden',
      collapsed ? 'w-[72px]' : 'w-64'
    )}>
      {/* Brand header */}
      <div className={cn(
        'flex items-center border-b border-line shrink-0',
        collapsed ? 'px-3 py-5 justify-center' : 'gap-3 px-4 py-5'
      )}>
        <div className="w-9 h-9 rounded-[10px] bg-primary flex items-center justify-center text-ink-100 font-extrabold text-base shrink-0">
          Б
        </div>
        {!collapsed && (
          <div className="flex-1 min-w-0">
            <div className="text-sm font-bold text-ink-100 leading-tight">БережЕда</div>
            <div className="text-[11px] text-ink-40 leading-tight">{t('nav.profile')}</div>
          </div>
        )}
        <button
          onClick={onToggle}
          title={collapsed ? 'Развернуть' : 'Свернуть'}
          className={cn(
            'p-1.5 rounded-[8px] text-ink-40 hover:text-ink-100 hover:bg-line transition-colors shrink-0',
            collapsed && 'mt-2 self-center'
          )}
        >
          <PanelLeft className={cn(
            'h-4 w-4 transition-transform duration-200',
            collapsed && 'rotate-180'
          )} />
        </button>
      </div>

      {/* Nav */}
      <nav className={cn('flex-1 py-3 overflow-y-auto space-y-0.5', collapsed ? 'px-2' : 'px-4')}>
        {navItems.map(item => {
          const Icon = item.icon
          const isActive = item.id === 'home'
            ? pathname === item.href
            : pathname.startsWith(item.href) &&
              !navItems.some(
                other => other.id !== item.id &&
                         other.href.startsWith(item.href) &&
                         other.href !== item.href &&
                         pathname.startsWith(other.href)
              )
          return (
            <Link
              key={item.id}
              href={item.href}
              title={collapsed ? t(item.labelKey) : undefined}
              className={cn(
                'relative flex items-center gap-3 py-2.5 rounded-[10px] text-sm transition-colors',
                collapsed ? 'justify-center px-2' : 'px-3',
                isActive
                  ? 'bg-primary-soft text-ink-100 font-semibold'
                  : 'text-ink-60 hover:bg-line/60 hover:text-ink-100'
              )}
            >
              {isActive && !collapsed && (
                <span className="absolute left-0 top-2 bottom-2 w-[3px] bg-primary rounded-r-full" />
              )}
              <span className="relative shrink-0">
                <Icon className="h-[18px] w-[18px]" />
                {collapsed && item.id === 'notifs' && unread > 0 && (
                  <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-accent" />
                )}
              </span>
              {!collapsed && <span className="flex-1">{t(item.labelKey)}</span>}
              {!collapsed && item.id === 'notifs' && unread > 0 && (
                <span className="min-w-[20px] h-5 px-1 rounded-full bg-accent text-white text-[11px] font-bold flex items-center justify-center">
                  {unread > 99 ? '99+' : unread}
                </span>
              )}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
