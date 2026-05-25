'use client'
import { useEffect, useState } from 'react'
import { Bell, ShoppingBag, AlertCircle, Wallet, Info, Star } from 'lucide-react'
import { getMyNotifications, markNotificationRead } from '@/lib/api'

const TYPE_ICON: Record<string, React.ReactNode> = {
  sale:    <ShoppingBag size={16} strokeWidth={1.8} />,
  alert:   <AlertCircle size={16} strokeWidth={1.8} />,
  payout:  <Wallet size={16} strokeWidth={1.8} />,
  system:  <Info size={16} strokeWidth={1.8} />,
  review:  <Star size={16} strokeWidth={1.8} />,
}

const TYPE_COLOR: Record<string, { bg: string; color: string }> = {
  sale:    { bg: '#EAF3ED', color: '#2E7D5B' },
  alert:   { bg: '#FFEDE7', color: '#E8553D' },
  payout:  { bg: '#FFF8E1', color: '#8a6d00' },
  system:  { bg: '#f0f0f0', color: '#4a4a4a' },
  review:  { bg: '#FFF4DE', color: '#C88A1B' },
}

function groupByDate(notifs: any[]) {
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1)
  const weekAgo = new Date(today); weekAgo.setDate(weekAgo.getDate() - 7)

  const groups: { label: string; items: any[] }[] = [
    { label: 'Сегодня', items: [] },
    { label: 'Вчера', items: [] },
    { label: 'На неделе', items: [] },
    { label: 'Ранее', items: [] },
  ]
  notifs.forEach(n => {
    const d = new Date(n.created_at); d.setHours(0, 0, 0, 0)
    if (d >= today) groups[0].items.push(n)
    else if (d >= yesterday) groups[1].items.push(n)
    else if (d >= weekAgo) groups[2].items.push(n)
    else groups[3].items.push(n)
  })
  return groups.filter(g => g.items.length > 0)
}

export default function SellerNotificationsPage() {
  const [notifs, setNotifs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'unread'>('all')

  useEffect(() => {
    getMyNotifications().then(data => {
      setNotifs(data.data || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const handleRead = async (id: string) => {
    await markNotificationRead(id).catch(() => {})
    setNotifs(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n))
  }

  const filtered = filter === 'unread' ? notifs.filter(n => !n.is_read) : notifs
  const unreadCount = notifs.filter(n => !n.is_read).length
  const groups = groupByDate(filtered)

  return (
    <div style={{ padding: '24px 32px 48px', maxWidth: 720, margin: '0 auto' }}>

      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 mb-5">
        <div
          className="inline-flex gap-0.5 p-0.5"
          style={{ background: '#f7f6f3', borderRadius: 9 }}
        >
          {(['all', 'unread'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className="transition-all font-semibold flex items-center gap-1.5"
              style={{
                padding: '6px 12px',
                borderRadius: 7,
                fontSize: 12.5,
                color: filter === f ? '#1a1a1a' : '#8a8a8a',
                background: filter === f ? '#ffffff' : 'transparent',
                boxShadow: filter === f ? '0 1px 2px rgba(20,20,20,.04), 0 0 0 1px rgba(20,20,20,.04)' : 'none',
              }}
            >
              {f === 'all' ? 'Все' : 'Непрочитанные'}
              {f === 'unread' && unreadCount > 0 && (
                <span
                  className="font-bold"
                  style={{
                    background: '#E8553D', color: 'white',
                    fontSize: 10.5, minWidth: 18, height: 18,
                    borderRadius: 999, display: 'grid', placeItems: 'center', padding: '0 5px',
                  }}
                >
                  {unreadCount}
                </span>
              )}
            </button>
          ))}
        </div>

        {unreadCount > 0 && (
          <button
            className="font-semibold transition-colors"
            style={{ fontSize: 13, color: '#8a8a8a' }}
            onMouseEnter={e => { (e.currentTarget.style.color = '#1a1a1a') }}
            onMouseLeave={e => { (e.currentTarget.style.color = '#8a8a8a') }}
            onClick={() => {
              notifs.filter(n => !n.is_read).forEach(n => markNotificationRead(n.id).catch(() => {}))
              setNotifs(prev => prev.map(n => ({ ...n, is_read: true })))
            }}
          >
            Отметить все прочитанными
          </button>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-ink-40">
          <Bell size={40} className="mx-auto mb-3 opacity-30" />
          <p className="font-semibold" style={{ fontSize: 15 }}>
            {filter === 'unread' ? 'Нет непрочитанных' : 'Нет уведомлений'}
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-5">
          {groups.map(group => (
            <div key={group.label}>
              <p
                className="font-bold mb-2 text-eyebrow text-ink-40"
              >
                {group.label}
              </p>
              <div
                style={{
                  background: '#ffffff',
                  border: '1px solid #e1e0db',
                  borderRadius: 14,
                  overflow: 'hidden',
                }}
              >
                {group.items.map((n: any, idx: number) => {
                  const typeKey = n.type ?? 'system'
                  const tc = TYPE_COLOR[typeKey] || TYPE_COLOR.system
                  const icon = TYPE_ICON[typeKey] || TYPE_ICON.system
                  return (
                    <div
                      key={n.id}
                      onClick={() => !n.is_read && handleRead(n.id)}
                      className="flex items-start gap-3 transition-colors"
                      style={{
                        padding: '14px 16px',
                        borderTop: idx > 0 ? '1px solid #ececea' : 'none',
                        background: n.is_read ? '#ffffff' : '#FFF8E1',
                        cursor: n.is_read ? 'default' : 'pointer',
                      }}
                      onMouseEnter={e => { if (!n.is_read) (e.currentTarget.style.background = '#FFF4C2') }}
                      onMouseLeave={e => { if (!n.is_read) (e.currentTarget.style.background = '#FFF8E1') }}
                    >
                      {/* Icon */}
                      <div
                        className="grid place-items-center flex-shrink-0"
                        style={{
                          width: 34, height: 34, borderRadius: 9,
                          background: tc.bg, color: tc.color,
                          marginTop: 1,
                        }}
                      >
                        {icon}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div
                          className="leading-snug"
                          style={{ fontSize: 14, fontWeight: n.is_read ? 500 : 700, color: '#1a1a1a' }}
                        >
                          {n.title}
                        </div>
                        {n.body && (
                          <div className="mt-0.5 text-ink-60" style={{ fontSize: 13, lineHeight: 1.45 }}>
                            {n.body}
                          </div>
                        )}
                        <div className="mt-1.5 font-mono text-ink-40" style={{ fontSize: 11.5 }}>
                          {new Date(n.created_at).toLocaleString('ru', {
                            day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
                          })}
                        </div>
                      </div>

                      {/* Unread dot */}
                      {!n.is_read && (
                        <div
                          className="flex-shrink-0 rounded-full"
                          style={{ width: 8, height: 8, background: '#FFC629', marginTop: 6 }}
                        />
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
