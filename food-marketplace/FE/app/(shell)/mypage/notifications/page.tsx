'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Bell, ShoppingBag, Star, AlertTriangle, Package, CheckCheck, Loader2 } from 'lucide-react'
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '@/lib/api'

const PAGE_SIZE = 20

interface Notification {
  id: string
  title: string
  body: string
  notification_type?: string
  reference_id?: string
  is_read?: boolean
  created_at: string
}

function formatTime(raw: string) {
  const d = new Date(raw.endsWith('Z') ? raw : raw + 'Z')
  const now = Date.now()
  const diff = now - d.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Только что'
  if (mins < 60) return `${mins} мин. назад`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} ч. назад`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} дн. назад`
  return d.toLocaleDateString('ru-RU')
}

function groupLabel(raw: string): string {
  const d = new Date(raw.endsWith('Z') ? raw : raw + 'Z')
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000)
  if (diffDays === 0) return 'Сегодня'
  if (diffDays === 1) return 'Вчера'
  if (diffDays < 7) return 'На неделе'
  if (diffDays < 30) return 'В этом месяце'
  return 'Ранее'
}

function getNotifUrl(n: Notification): string | null {
  if (n.notification_type === 'combo_available' && n.reference_id) return `/combos/${n.reference_id}`
  return null
}

function NotifIcon({ type }: { type?: string }) {
  const base = "h-[18px] w-[18px]"
  if (type === 'combo_available' || type === 'NEW_COMBO_FROM_FAVORITE_STORE')
    return <Star className={`${base} text-warn`} />
  if (type === 'order_paid' || type === 'USER_BUY_COMBO' || type === 'USER_CANCELLED_COMBO')
    return <ShoppingBag className={`${base} text-blue-500`} />
  if (type === 'COMBO_PICKUP_DEADLINE_APPROACHING')
    return <AlertTriangle className={`${base} text-warn`} />
  if (type === 'order_expired' || type === 'ORDER_CANCELED' || type === 'COMBO_PICKUP_DEADLINE_PASSED')
    return <AlertTriangle className={`${base} text-accent`} />
  if (type === 'PRODUCT_EXPIRED' || type === 'PRODUCT_EXPIRY_REACHED')
    return <Package className={`${base} text-ink-60`} />
  return <Bell className={`${base} text-ink-40`} />
}

function notifIconBg(type?: string) {
  if (type === 'combo_available' || type === 'NEW_COMBO_FROM_FAVORITE_STORE') return 'bg-primary-soft'
  if (type === 'order_paid' || type === 'USER_BUY_COMBO') return 'bg-blue-50'
  if (type === 'order_expired' || type === 'ORDER_CANCELED' || type === 'COMBO_PICKUP_DEADLINE_PASSED') return 'bg-accent-soft'
  if (type === 'COMBO_PICKUP_DEADLINE_APPROACHING') return 'bg-warn-soft'
  return 'bg-line/60'
}

export default function NotificationsPage() {
  const router = useRouter()
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [markingAll, setMarkingAll] = useState(false)
  const [tab, setTab] = useState<'all' | 'unread'>('all')
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const loaderRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getNotifications()
      .then((r: any) => setNotifications(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  // Reset visible count when tab changes
  useEffect(() => {
    setVisibleCount(PAGE_SIZE)
  }, [tab])

  // IntersectionObserver for infinite scroll
  const setupObserver = useCallback(() => {
    const el = loaderRef.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisibleCount(c => c + PAGE_SIZE)
        }
      },
      { threshold: 0.1 }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!loading) return setupObserver()
  }, [loading, setupObserver])

  async function handleMarkRead(id: string) {
    setNotifications(ns => ns.map(n => n.id === id ? { ...n, is_read: true } : n))
    await markNotificationRead(id).catch(() => {})
  }

  async function handleMarkAllRead() {
    setMarkingAll(true)
    try {
      await markAllNotificationsRead()
      setNotifications(ns => ns.map(n => ({ ...n, is_read: true })))
    } catch {}
    finally { setMarkingAll(false) }
  }

  const unreadCount = notifications.filter(n => !n.is_read).length
  const allDisplayed = tab === 'unread' ? notifications.filter(n => !n.is_read) : notifications
  const visible = allDisplayed.slice(0, visibleCount)
  const hasMore = visibleCount < allDisplayed.length

  // Group visible items by time label
  const grouped: Record<string, Notification[]> = {}
  const groupOrder: string[] = []
  for (const n of visible) {
    const lbl = groupLabel(n.created_at)
    if (!grouped[lbl]) { grouped[lbl] = []; groupOrder.push(lbl) }
    grouped[lbl].push(n)
  }

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-5 max-w-[800px] mx-auto w-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-1 bg-line/60 rounded-[8px] p-0.5">
          <button
            onClick={() => setTab('all')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] text-sm font-semibold transition-colors ${
              tab === 'all' ? 'bg-surface text-ink-100 shadow-sm' : 'text-ink-60 hover:text-ink-100'
            }`}
          >
            Все
            <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-line text-ink-60">{notifications.length}</span>
          </button>
          <button
            onClick={() => setTab('unread')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] text-sm font-semibold transition-colors ${
              tab === 'unread' ? 'bg-surface text-ink-100 shadow-sm' : 'text-ink-60 hover:text-ink-100'
            }`}
          >
            Непрочитанные
            <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-line text-ink-60">{unreadCount}</span>
          </button>
        </div>

        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            disabled={markingAll}
            className="flex items-center gap-1.5 text-sm font-semibold text-ink-60 border border-line rounded-[10px] px-3 py-2 hover:bg-line/60 transition-colors disabled:opacity-50"
          >
            <CheckCheck className="h-4 w-4" />
            Прочитать все
          </button>
        )}
      </div>

      {loading && (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      )}

      {!loading && allDisplayed.length === 0 && (
        <div className="bg-surface rounded-card shadow-sm flex flex-col items-center py-20 text-center">
          <Bell className="h-14 w-14 text-line2 mb-4" />
          <p className="font-semibold text-ink-60">Нет уведомлений</p>
          <p className="text-sm text-ink-40 mt-1">Здесь будут появляться уведомления о новых товарах и заказах</p>
        </div>
      )}

      {!loading && visible.length > 0 && (
        <div className="space-y-6">
          {groupOrder.map(lbl => (
            <div key={lbl}>
              <div className="text-[11px] font-semibold text-ink-40 uppercase tracking-wider mb-3 px-0.5">{lbl}</div>
              <div className="bg-surface rounded-card shadow-sm overflow-hidden divide-y divide-line">
                {grouped[lbl].map(n => {
                  const url = getNotifUrl(n)
                  return (
                    <div
                      key={n.id}
                      onClick={() => {
                        if (!n.is_read) handleMarkRead(n.id)
                        if (url) router.push(url)
                      }}
                      className={`flex items-start gap-4 px-4 py-4 transition-colors ${
                        n.is_read ? 'opacity-60' : ''
                      } ${url ? 'cursor-pointer hover:bg-bg/60' : 'cursor-default'}`}
                    >
                      <div className={`w-9 h-9 rounded-[10px] flex items-center justify-center shrink-0 mt-0.5 ${notifIconBg(n.notification_type)}`}>
                        <NotifIcon type={n.notification_type} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2 mb-0.5">
                          <p className={`text-sm leading-snug ${!n.is_read ? 'font-semibold text-ink-100' : 'text-ink-60'}`}>
                            {n.title}
                          </p>
                          <span className="text-[11px] text-ink-40 shrink-0 mt-0.5">{formatTime(n.created_at)}</span>
                        </div>
                        {n.body && <p className="text-xs text-ink-40 leading-relaxed">{n.body}</p>}
                      </div>
                      {!n.is_read && <div className="w-2.5 h-2.5 rounded-full bg-primary shrink-0 mt-1.5" />}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}

          {/* Infinite scroll sentinel */}
          <div ref={loaderRef} className="flex justify-center py-4">
            {hasMore && <Loader2 className="h-5 w-5 animate-spin text-ink-40" />}
          </div>
        </div>
      )}
    </div>
  )
}
