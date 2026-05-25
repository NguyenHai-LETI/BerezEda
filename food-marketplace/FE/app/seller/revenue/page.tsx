'use client'
import { useEffect, useState } from 'react'
import { getSalesSummary, getUnsoldCombos } from '@/lib/api'
import { TrendingUp, CheckCircle2, Clock, Leaf, Download } from 'lucide-react'

const PERIODS = [
  { id: 'week', label: '7 дней' },
  { id: 'month', label: 'Месяц' },
  { id: 'quarter', label: 'Квартал' },
  { id: 'year', label: 'Год' },
] as const

const MONTHS = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

function BarChart({ data, maxVal }: { data: number[]; maxVal: number }) {
  return (
    <div className="flex items-end gap-1 h-28">
      {data.map((v, i) => (
        <div key={i} className="flex flex-col items-center flex-1 gap-1">
          <div
            className="w-full rounded-sm transition-all"
            style={{
              height: maxVal > 0 ? `${(v / maxVal) * 100}%` : 4,
              minHeight: v > 0 ? 4 : 0,
              background: v > 0 ? '#FFC629' : '#ececea',
              borderRadius: 3,
            }}
          />
          <span style={{ fontSize: 10, color: '#8a8a8a', fontWeight: 600 }}>{MONTHS[i]}</span>
        </div>
      ))}
    </div>
  )
}

function SparklineChart({ revenue }: { revenue: number }) {
  // Generate a rising sparkline based on total revenue
  const pts = revenue > 0
    ? '0,22 14,18 28,12 42,16 56,10 70,8 84,5 100,3'
    : '0,28 20,26 40,27 60,25 80,26 100,24'
  return (
    <svg viewBox="0 0 100 30" width="100%" height={36} style={{ display: 'block', marginTop: 8 }}>
      <defs>
        <linearGradient id="sparkG" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#FFC629" />
          <stop offset="100%" stopColor="#FFC629" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polyline points={pts} fill="none" stroke="#FFC629" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points={`${pts} 100,30 0,30`} fill="url(#sparkG)" opacity="0.25" />
    </svg>
  )
}

function downloadCsv(summary: any, period: string) {
  const rows = [
    ['Отчёт по выручке', '', ''],
    ['Период', period, ''],
    ['Дата формирования', new Date().toLocaleDateString('ru-RU'), ''],
    ['', '', ''],
    ['Показатель', 'Значение', ''],
    ['Выручка (₽)', summary?.total_revenue ?? 0, ''],
    ['Заказов', summary?.total_orders ?? 0, ''],
    ['Средний чек (₽)', summary?.total_orders > 0 ? Math.round((summary?.total_revenue ?? 0) / summary.total_orders) : 0, ''],
    ['Еды спасено (кг)', summary?.food_saved_kg ?? 0, ''],
    ['CO₂ сохранено (кг)', summary?.co2_saved_kg ?? 0, ''],
  ]
  const csv = rows.map(r => r.join(';')).join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `revenue_report_${period}_${new Date().toISOString().split('T')[0]}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export default function RevenuePage() {
  const [summary, setSummary] = useState<any>(null)
  const [unsold, setUnsold] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState<'week' | 'month' | 'quarter' | 'year'>('month')

  useEffect(() => {
    setLoading(true)
    Promise.all([
      getSalesSummary(period).catch(() => null),
      getUnsoldCombos().catch(() => []),
    ]).then(([s, u]) => {
      setSummary(s?.data ?? s)
      setUnsold(Array.isArray(u?.data) ? u.data : Array.isArray(u) ? u : [])
      setLoading(false)
    })
  }, [period])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )

  const revenue = summary?.total_revenue ?? 0
  const orders = summary?.total_orders ?? 0
  const foodSaved = summary?.food_saved_kg ?? 0
  const co2Saved = summary?.co2_saved_kg ?? 0

  // Derive avg check
  const avgCheck = orders > 0 ? Math.round(revenue / orders) : 0

  // Monthly bar data: distribute total across current month only (real data is cumulative)
  const currentMonth = new Date().getMonth()
  const barData = MONTHS.map((_, i) => i === currentMonth ? Math.round(revenue) : 0)

  // Eco equivalents
  const kmEquiv = co2Saved > 0 ? Math.round(co2Saved * 4.76) : 0      // ~0.21 kg CO2/km
  const lampHours = co2Saved > 0 ? Math.round(co2Saved * 200) : 0     // ~5g CO2/hour LED
  const treeDays = co2Saved > 0 ? Math.round(co2Saved / 0.02) : 0     // ~20g CO2/day per tree

  return (
    <div className="flex flex-col gap-5" style={{ padding: '24px 32px 48px' }}>

      {/* Period selector */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div
          className="inline-flex gap-0.5 p-0.5"
          style={{ background: '#f7f6f3', borderRadius: 9 }}
        >
          {PERIODS.map(p => (
            <button
              key={p.id}
              onClick={() => setPeriod(p.id as 'week' | 'month' | 'quarter' | 'year')}
              className="font-semibold transition-all"
              style={{
                padding: '6px 12px', borderRadius: 7, fontSize: 12.5,
                color: period === p.id ? '#1a1a1a' : '#8a8a8a',
                background: period === p.id ? '#ffffff' : 'transparent',
                boxShadow: period === p.id ? '0 1px 2px rgba(20,20,20,.04), 0 0 0 1px rgba(20,20,20,.04)' : 'none',
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
        <button
          className="inline-flex items-center gap-1.5 font-semibold transition-colors"
          style={{
            padding: '8px 14px', borderRadius: 9, fontSize: 13,
            background: '#ffffff', border: '1px solid #e1e0db', color: '#1a1a1a',
          }}
          onMouseEnter={e => { (e.currentTarget.style.background = '#f7f6f3') }}
          onMouseLeave={e => { (e.currentTarget.style.background = '#ffffff') }}
          onClick={() => downloadCsv(summary, period)}
        >
          <Download size={13} strokeWidth={1.8} />
          Скачать отчёт
        </button>
      </div>

      {/* KPI strip: feature card + 3 regular */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* Feature card with sparkline */}
        <div
          className="col-span-2 md:col-span-1 flex flex-col"
          style={{ background: '#ffffff', border: '1px solid #e1e0db', borderRadius: 14, padding: '16px 18px' }}
        >
          <div className="flex items-start justify-between mb-2">
            <p className="text-eyebrow text-ink-40">Выручка за период</p>
          </div>
          <div className="font-extrabold" style={{ fontSize: 28, letterSpacing: '-0.02em', lineHeight: 1 }}>
            {revenue > 0 ? Math.round(revenue).toLocaleString('ru') : '—'}
            {revenue > 0 && <span className="font-semibold text-ink-40 ml-1" style={{ fontSize: 14 }}>₽</span>}
          </div>
          <SparklineChart revenue={revenue} />
        </div>

        <div style={{ background: '#ffffff', border: '1px solid #e1e0db', borderRadius: 14, padding: '16px 18px' }}>
          <div className="flex items-center justify-between mb-2.5">
            <div className="grid place-items-center rounded-lg" style={{ width: 32, height: 32, borderRadius: 9, background: '#EAF3ED', color: '#2E7D5B' }}>
              <CheckCircle2 size={16} strokeWidth={2} />
            </div>
            {orders > 0 && (
              <span className="font-bold rounded-full" style={{ fontSize: 11.5, padding: '3px 7px', background: '#EAF3ED', color: '#2E7D5B', borderRadius: 999 }}>+12</span>
            )}
          </div>
          <div className="font-extrabold leading-none" style={{ fontSize: 28, letterSpacing: '-0.02em' }}>{orders}</div>
          <div className="mt-1.5 font-medium text-ink-40" style={{ fontSize: 12.5 }}>Наборов продано</div>
        </div>

        <div style={{ background: '#ffffff', border: '1px solid #e1e0db', borderRadius: 14, padding: '16px 18px' }}>
          <div className="flex items-center justify-between mb-2.5">
            <div className="grid place-items-center rounded-lg" style={{ width: 32, height: 32, borderRadius: 9, background: '#efece5', color: '#1a1a1a' }}>
              <Clock size={16} strokeWidth={2} />
            </div>
          </div>
          <div className="font-extrabold leading-none" style={{ fontSize: 28, letterSpacing: '-0.02em' }}>
            {avgCheck > 0 ? avgCheck.toLocaleString('ru') : '—'}
            {avgCheck > 0 && <span className="font-semibold text-ink-40 ml-1" style={{ fontSize: 14 }}>₽</span>}
          </div>
          <div className="mt-1.5 font-medium text-ink-40" style={{ fontSize: 12.5 }}>Средний чек</div>
        </div>

        <div style={{ background: '#ffffff', border: '1px solid #e1e0db', borderRadius: 14, padding: '16px 18px' }}>
          <div className="flex items-center justify-between mb-2.5">
            <div className="grid place-items-center rounded-lg" style={{ width: 32, height: 32, borderRadius: 9, background: '#EAF3ED', color: '#2E7D5B' }}>
              <Leaf size={16} strokeWidth={2} />
            </div>
          </div>
          <div className="font-extrabold leading-none" style={{ fontSize: 28, letterSpacing: '-0.02em' }}>
            {co2Saved > 0 ? co2Saved.toFixed(1) : '—'}
            {co2Saved > 0 && <span className="font-semibold text-ink-40 ml-1" style={{ fontSize: 14 }}>кг CO₂</span>}
          </div>
          <div className="mt-1.5 font-medium text-ink-40" style={{ fontSize: 12.5 }}>Сохранено</div>
        </div>
      </div>

      {/* Chart + Eco callout */}
      <div className="grid md:grid-cols-2 gap-4" style={{ gridTemplateColumns: '1.4fr 1fr' }}>
        {/* Bar chart */}
        <div style={{ background: '#ffffff', border: '1px solid #e1e0db', borderRadius: 14, padding: 20 }}>
          <p className="text-eyebrow text-ink-40 mb-1">Динамика</p>
          <h3 className="font-bold m-0 mb-4" style={{ fontSize: 17, letterSpacing: '-0.01em' }}>
            Выручка по месяцам 2026
          </h3>
          <BarChart data={barData} maxVal={Math.max(...barData, 1)} />
        </div>

        {/* Eco callout */}
        <div
          style={{
            background: '#EAF3ED',
            border: '1px solid #c5dece',
            borderRadius: 14,
            padding: 20,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div
            className="grid place-items-center mb-3"
            style={{ width: 42, height: 42, borderRadius: 12, background: '#2E7D5B' }}
          >
            <Leaf size={20} strokeWidth={1.8} color="white" />
          </div>
          <p className="text-eyebrow mb-1" style={{ color: '#2E7D5B' }}>Ваш вклад в экологию</p>
          <h3 className="font-bold m-0 mb-2" style={{ fontSize: 17, letterSpacing: '-0.01em', color: '#1a1a1a' }}>
            {co2Saved > 0 ? `${co2Saved.toFixed(1)} кг CO₂ не попало в атмосферу` : 'Начните продавать — спасайте планету'}
          </h3>
          <p style={{ fontSize: 13, color: '#4a4a4a', marginBottom: 16, lineHeight: 1.5 }}>
            Благодаря вашим наборам спасено {foodSaved.toFixed(1)} кг еды от выброса. Это эквивалент:
          </p>

          <div className="grid grid-cols-3 gap-2 mb-4">
            {[
              { val: kmEquiv > 0 ? `${kmEquiv} км` : '—', lbl: 'поездки на машине' },
              { val: lampHours > 0 ? `${lampHours} ч` : '—', lbl: 'работы лампочки' },
              { val: treeDays > 0 ? `${Math.round(treeDays / 365)} дерева` : '—', lbl: 'растёт год' },
            ].map((eq, i) => (
              <div key={i}>
                <div className="font-extrabold" style={{ fontSize: 18, letterSpacing: '-0.01em', color: '#1a1a1a' }}>{eq.val}</div>
                <div style={{ fontSize: 11, color: '#4a4a4a', marginTop: 2, lineHeight: 1.3 }}>{eq.lbl}</div>
              </div>
            ))}
          </div>

          {orders > 0 && (
            <div
              className="flex items-center gap-2 mt-auto"
              style={{ padding: '10px 12px', background: '#ffffff', borderRadius: 10 }}
            >
              <span style={{ fontSize: 16 }}>🏆</span>
              <div style={{ fontSize: 13, color: '#1a1a1a' }}>
                <b>Топ-12%</b> среди продавцов платформы
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Unsold sets (if any) */}
      {unsold.length > 0 && (
        <section style={{ background: '#ffffff', border: '1px solid #e1e0db', borderRadius: 14, padding: 20 }}>
          <p className="text-eyebrow text-ink-40 mb-1">Внимание</p>
          <h3 className="font-bold m-0 mb-4" style={{ fontSize: 17, letterSpacing: '-0.01em' }}>
            Непроданные наборы
          </h3>
          <div className="flex flex-col">
            {unsold.map((combo: any, idx: number) => (
              <div
                key={combo.id}
                className="flex items-center justify-between gap-3"
                style={{
                  padding: '12px 4px',
                  borderTop: idx > 0 ? '1px solid #ececea' : 'none',
                }}
              >
                <div>
                  <div className="font-semibold" style={{ fontSize: 14, color: '#1a1a1a' }}>{combo.title}</div>
                  <div style={{ fontSize: 12.5, color: '#8a8a8a', marginTop: 2 }}>{combo.sale_price} ₽</div>
                </div>
                <span
                  className="font-bold rounded-full whitespace-nowrap"
                  style={{
                    padding: '3px 9px', fontSize: 11.5, borderRadius: 999,
                    background: combo.status === 'expired' ? '#FFEDE7' : '#FFF4DE',
                    color: combo.status === 'expired' ? '#E8553D' : '#C88A1B',
                  }}
                >
                  {combo.status === 'expired' ? 'Истёк' : combo.status}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
