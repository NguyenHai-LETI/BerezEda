'use client'
import { useEffect, useState } from 'react'
import { getSalesHistory } from '@/lib/api'
import { TrendingUp, CheckCircle2, Clock, Leaf, Download, Calendar } from 'lucide-react'

const RANGES = [
  { id: 'today', label: 'Сегодня' },
  { id: 'week', label: 'Неделя' },
  { id: 'month', label: 'Месяц' },
  { id: 'all', label: 'Всё время' },
] as const

function rangeToDate(range: string): string {
  const now = new Date()
  switch (range) {
    case 'today': return now.toISOString().split('T')[0]
    case 'week': {
      const d = new Date(now); d.setDate(d.getDate() - 7)
      return d.toISOString().split('T')[0]
    }
    case 'month': {
      const d = new Date(now); d.setDate(d.getDate() - 30)
      return d.toISOString().split('T')[0]
    }
    default: return '2024-01-01'
  }
}

function formatRangeLabel(range: string): string {
  const today = new Date()
  const fmt = (d: Date) => d.toLocaleDateString('ru', { day: 'numeric', month: 'short' })
  switch (range) {
    case 'today': return fmt(today)
    case 'week': {
      const start = new Date(today); start.setDate(start.getDate() - 7)
      return `${fmt(start)} – ${fmt(today)}`
    }
    case 'month': {
      const start = new Date(today); start.setDate(start.getDate() - 30)
      return `${fmt(start)} – ${fmt(today)}`
    }
    default: return 'за всё время'
  }
}

// Build 24-hour distribution from orders
function buildHourlyBars(orders: any[]): number[] {
  const counts = new Array(24).fill(0)
  orders.forEach(o => {
    if (o.created_at) {
      const h = new Date(o.created_at).getHours()
      counts[h] += 1
    }
  })
  return counts
}

function exportOrdersCsv(orders: any[], range: string) {
  const header = ['Время', 'Набор', 'Сумма (₽)', 'Статус']
  const rows = orders.map(o => [
    new Date(o.created_at).toLocaleString('ru', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }),
    o.combo_title || 'Набор',
    o.amount ?? '',
    o.status === 'refunded' ? 'Возврат' : 'Оплачен',
  ])
  const csv = [header, ...rows].map(r => r.join(';')).join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `sales_${range}_${new Date().toISOString().split('T')[0]}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export default function SalesHistoryPage() {
  const [orders, setOrders] = useState<any[]>([])
  const [range, setRange] = useState<string>('today')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getSalesHistory(rangeToDate(range)).then(data => {
      setOrders(data.data || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [range])

  const total = orders.reduce((sum, o) => sum + (o.amount || 0), 0)
  const avgCheck = orders.length > 0 ? Math.round(total / orders.length) : 0
  const hourly = buildHourlyBars(orders)
  const maxHour = Math.max(...hourly, 1)

  return (
    <div className="flex flex-col gap-5" style={{ padding: '24px 32px 48px' }}>

      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          <div
            className="inline-flex gap-0.5 p-0.5"
            style={{ background: '#f7f6f3', borderRadius: 9 }}
          >
            {RANGES.map(r => (
              <button
                key={r.id}
                onClick={() => setRange(r.id)}
                className="font-semibold transition-all"
                style={{
                  padding: '6px 12px', borderRadius: 7, fontSize: 12.5,
                  color: range === r.id ? '#1a1a1a' : '#8a8a8a',
                  background: range === r.id ? '#ffffff' : 'transparent',
                  boxShadow: range === r.id ? '0 1px 2px rgba(20,20,20,.04), 0 0 0 1px rgba(20,20,20,.04)' : 'none',
                }}
              >
                {r.label}
              </button>
            ))}
          </div>

          <div
            className="inline-flex items-center gap-1.5 font-semibold"
            style={{
              padding: '6px 12px', borderRadius: 9, fontSize: 13,
              background: '#ffffff', border: '1px solid #e1e0db', color: '#4a4a4a',
            }}
          >
            <Calendar size={13} strokeWidth={1.8} />
            {formatRangeLabel(range)}
          </div>
        </div>

        <button
          className="inline-flex items-center gap-1.5 font-semibold transition-colors"
          style={{
            padding: '8px 14px', borderRadius: 9, fontSize: 13,
            background: '#ffffff', border: '1px solid #e1e0db', color: '#1a1a1a',
          }}
          onMouseEnter={e => { (e.currentTarget.style.background = '#f7f6f3') }}
          onMouseLeave={e => { (e.currentTarget.style.background = '#ffffff') }}
          onClick={() => exportOrdersCsv(orders, range)}
          disabled={orders.length === 0}
        >
          <Download size={13} strokeWidth={1.8} />
          Экспорт
        </button>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { icon: <TrendingUp size={16} strokeWidth={2} />, iconBg: '#FFF8E1', iconColor: '#8a6d00',
            value: total > 0 ? `${Math.round(total).toLocaleString('ru')} ₽` : '—', label: 'Выручка за период',
            trend: orders.length > 0 ? '+12%' : undefined },
          { icon: <CheckCircle2 size={16} strokeWidth={2} />, iconBg: '#EAF3ED', iconColor: '#2E7D5B',
            value: orders.length, label: 'Продажи' },
          { icon: <Clock size={16} strokeWidth={2} />, iconBg: '#efece5', iconColor: '#1a1a1a',
            value: avgCheck > 0 ? `${avgCheck.toLocaleString('ru')} ₽` : '—', label: 'Средний чек' },
          { icon: <Leaf size={16} strokeWidth={2} />, iconBg: '#EAF3ED', iconColor: '#2E7D5B',
            value: orders.length > 0 ? `${(orders.length * 0.5).toFixed(1)} кг` : '—', label: 'Сохранено CO₂' },
        ].map((k, i) => (
          <div key={i} style={{ background: '#ffffff', border: '1px solid #e1e0db', borderRadius: 14, padding: '16px 18px' }}>
            <div className="flex items-center justify-between mb-2.5">
              <div className="grid place-items-center rounded-lg" style={{ width: 32, height: 32, borderRadius: 9, background: k.iconBg, color: k.iconColor }}>
                {k.icon}
              </div>
              {k.trend && (
                <span className="font-bold rounded-full" style={{ fontSize: 11.5, padding: '3px 7px', background: '#EAF3ED', color: '#2E7D5B', borderRadius: 999 }}>
                  {k.trend}
                </span>
              )}
            </div>
            <div className="font-extrabold leading-none" style={{ fontSize: 28, letterSpacing: '-0.02em' }}>{k.value}</div>
            <div className="mt-1.5 font-medium text-ink-40" style={{ fontSize: 12.5 }}>{k.label}</div>
          </div>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : (
        <>
          {/* Hourly distribution chart */}
          {orders.length > 0 && (
            <section style={{ background: '#ffffff', border: '1px solid #e1e0db', borderRadius: 14, padding: 20 }}>
              <div className="flex items-start justify-between gap-4 mb-4 flex-wrap">
                <div>
                  <p className="text-eyebrow text-ink-40 mb-1">График продаж</p>
                  <h3 className="font-bold m-0" style={{ fontSize: 17, letterSpacing: '-0.01em' }}>
                    Распределение по часам
                  </h3>
                </div>
                <div className="flex items-center gap-3" style={{ fontSize: 12, color: '#8a8a8a' }}>
                  <span className="flex items-center gap-1.5">
                    <span className="rounded-sm inline-block" style={{ width: 10, height: 10, background: '#FFC629', borderRadius: 2 }} />
                    Текущий период
                  </span>
                </div>
              </div>
              <div className="flex items-end gap-px" style={{ height: 80 }}>
                {hourly.map((v, i) => (
                  <div key={i} className="flex flex-col items-center flex-1 gap-0.5">
                    <div
                      className="w-full rounded-sm"
                      style={{
                        height: `${(v / maxHour) * 100}%`,
                        minHeight: v > 0 ? 3 : 0,
                        background: v > 0 ? '#FFC629' : '#ececea',
                        borderRadius: '2px 2px 0 0',
                      }}
                    />
                    {i % 4 === 0 && (
                      <span style={{ fontSize: 9, color: '#8a8a8a', fontWeight: 600 }}>
                        {String(i).padStart(2, '0')}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Sales table */}
          <section style={{ background: '#ffffff', border: '1px solid #e1e0db', borderRadius: 14, padding: 20 }}>
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <p className="text-eyebrow text-ink-40 mb-1">Продажи</p>
                <h3 className="font-bold m-0" style={{ fontSize: 17, letterSpacing: '-0.01em' }}>
                  {orders.length} {orders.length === 1 ? 'операция' : orders.length < 5 ? 'операции' : 'операций'}
                  {' · '}
                  <span style={{ color: '#8a8a8a', fontWeight: 500 }}>{formatRangeLabel(range)}</span>
                </h3>
              </div>
            </div>

            {orders.length === 0 ? (
              <div className="text-center py-10 text-ink-40">
                <div className="text-4xl mb-2">📋</div>
                <p className="font-semibold" style={{ fontSize: 14 }}>Нет продаж за этот период</p>
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #ececea' }}>
                    {['Время', 'Набор', 'Сумма', 'Статус'].map(h => (
                      <th
                        key={h}
                        className="text-left font-bold text-ink-40"
                        style={{ padding: '8px 8px 10px', fontSize: 11.5, letterSpacing: '0.04em', textTransform: 'uppercase' }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order: any, idx: number) => (
                    <tr
                      key={order.id}
                      style={{ borderTop: idx > 0 ? '1px solid #ececea' : 'none' }}
                    >
                      <td style={{ padding: '12px 8px' }}>
                        <span className="font-mono font-semibold" style={{ fontSize: 13, color: '#1a1a1a' }}>
                          {new Date(order.created_at).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </td>
                      <td style={{ padding: '12px 8px' }}>
                        <span className="font-semibold" style={{ fontSize: 14, color: '#1a1a1a' }}>
                          {order.combo_title || 'Набор'}
                        </span>
                      </td>
                      <td style={{ padding: '12px 8px', textAlign: 'right' }}>
                        <span className="font-bold" style={{ fontSize: 14, color: '#1a1a1a' }}>
                          {order.amount} ₽
                        </span>
                      </td>
                      <td style={{ padding: '12px 8px', textAlign: 'right' }}>
                        <span
                          className="font-bold rounded-full whitespace-nowrap"
                          style={{
                            padding: '3px 9px', fontSize: 11.5, borderRadius: 999,
                            background: order.status === 'refunded' ? '#FFEDE7' : '#EAF3ED',
                            color: order.status === 'refunded' ? '#E8553D' : '#2E7D5B',
                          }}
                        >
                          {order.status === 'refunded' ? 'Возврат' : 'Оплачен'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </div>
  )
}
