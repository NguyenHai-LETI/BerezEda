'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, History, MapPin, Heart, Bell, User } from 'lucide-react'
import { routes } from '@/lib/routes'
import { cn } from '@/lib/utils'
import { useI18n } from '@/contexts/I18nContext'

export function BottomNav() {
  const pathname = usePathname()
  const { t } = useI18n()

  const navItems = [
    { id: 'home',      icon: Home,    labelKey: 'bottom_nav.home',          href: routes.home },
    { id: 'history',   icon: History, labelKey: 'bottom_nav.history',       href: routes.history },
    { id: 'map',       icon: MapPin,  labelKey: 'bottom_nav.map',           href: routes.map },
    { id: 'favorites', icon: Heart,   labelKey: 'bottom_nav.favorites',     href: routes.favorites },
    { id: 'notifs',    icon: Bell,    labelKey: 'bottom_nav.notifications',  href: routes.notifications },
    { id: 'mypage',    icon: User,    labelKey: 'bottom_nav.profile',       href: routes.myPage },
  ] as const

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 bg-surface border-t border-line lg:hidden"
      aria-label="Bottom navigation"
    >
      <div className="flex items-center justify-around h-14 px-1">
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
              className={cn(
                'flex flex-col items-center justify-center flex-1 h-full gap-0.5 transition-colors rounded-md',
                isActive ? 'text-primary' : 'text-ink-40'
              )}
              aria-label={t(item.labelKey)}
            >
              <Icon className="h-5 w-5" />
              <span className="text-[10px] leading-tight">{t(item.labelKey)}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
