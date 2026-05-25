'use client'
import { useEffect, useState } from 'react'
import { getMyShop, getMyLockers, getMyCombos, getSalesSummary, cancelCombo } from '@/lib/api'
import { getFirestoreDb } from '@/lib/firebase'
import { collection, onSnapshot } from 'firebase/firestore'
import Link from 'next/link'
import Image from 'next/image'
import { ShoppingBasket, MoreHorizontal, Package, TrendingUp, CheckCircle2, Leaf, Plus } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { logout } from '@/lib/auth'
import ConfirmModal from '@/components/ConfirmModal'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
function imgUrl(path?: string) {
  if (!path) return null
  if (path.startsWith('http')) return path
  const base = API_URL.replace(/\/api\/?$/, '')
  return `${base}/uploads/${path.replace(/^\//, '')}`
}

interface UnitData {
  id: string
  unit_number: number
  status: string
  is_active: boolean
  temperature?: number | null
  combo_title?: string
  combo_status?: string
  sale_end_time?: string
}

interface LocationData {
  id: string
  name: string
  address: string
  units: UnitData[]
}

// ── Cell style by status ──────────────────────────────────────────────────────

const CELL_STYLE: Record<string, { bg: string; color: string; border: string; label: string }> = {
  AVAILABLE:   { bg: '#eaf6ee', color: '#1f6b40', border: '#d2ebd9', label: 'Свободна' },
  RESERVED:    { bg: '#fff4d6', color: '#7a5a00', border: '#f3e2a8', label: 'Забронирована' },
  OCCUPIED:    { bg: '#fde9e4', color: '#8a3a2a', border: '#f3cec3', label: 'Занята' },
  MAINTENANCE: { bg: '#ecedf0', color: '#6a6a6a', border: '#d8dadd', label: 'Обслуживание' },
}

const LEGEND_DOTS: Record<string, string> = {
  AVAILABLE:   '#b8dec5',
  RESERVED:    '#f5d97a',
  OCCUPIED:    '#f3b8a8',
  MAINTENANCE: '#c8cbcf',
}

// ── KPI card component ────────────────────────────────────────────────────────

function KpiCard({
  icon, iconBg, iconColor, value, unit, label, trend, trendColor,
}: {
  icon: React.ReactNode
  iconBg: string
  iconColor: string
  value: string | number
  unit?: string
  label: string
  trend?: string
  trendColor?: string
}) {
  return (
    <div
      className="flex flex-col"
      style={{
        background: '#ffffff',
        border: '1px solid #e1e0db',
        borderRadius: 14,
        padding: '16px 18px',
      }}
    >
      <div className="flex items-center justify-between mb-2.5">
        <div
          className="grid place-items-center rounded-lg"
          style={{ width: 32, height: 32, borderRadius: 9, background: iconBg, color: iconColor }}
        >
          {icon}
        </div>
        {trend && (
          <span
            className="font-bold rounded-full"
            style={{
              fontSize: 11.5,
              padding: '3px 7px',
              background: trendColor === 'eco' ? '#EAF3ED' : '#EAF3ED',
              color: trendColor === 'eco' ? '#2E7D5B' : '#2E7D5B',
            }}
          >
            {trend}
          </span>
        )}
      </div>
      <div className="font-extrabold leading-none" style={{ fontSize: 28, letterSpacing: '-0.02em' }}>
        {value}
        {unit && <span className="font-semibold text-ink-40 ml-1" style={{ fontSize: 14 }}>{unit}</span>}
      </div>
      <div className="mt-1.5 font-medium text-ink-40" style={{ fontSize: 12.5 }}>{label}</div>
    </div>
  )
}

// ── Postamat panel ────────────────────────────────────────────────────────────

function PostamatPanel({ locations }: { locations: LocationData[] }) {
  const [selectedId, setSelectedId] = useState(locations[0]?.id ?? '')
  const loc = locations.find(l => l.id === selectedId) ?? locations[0]
  const router = useRouter()
  const [confirmUnit, setConfirmUnit] = useState<{ locationId: string; unit: UnitData } | null>(null)

  function handleUnitClick(locationId: string, unit: UnitData) {
    if (unit.status !== 'AVAILABLE') return
    setConfirmUnit({ locationId, unit })
  }

  function handleConfirm() {
    if (!confirmUnit) return
    router.push(`/seller/add-item?locker_location_id=${confirmUnit.locationId}&locker_unit_id=${confirmUnit.unit.id}`)
    setConfirmUnit(null)
  }

  if (!loc) return null

  const freeCount = loc.units.filter(u => u.status === 'AVAILABLE').length
  const totalCount = loc.units.length

  return (
    <section
      style={{
        background: '#ffffff',
        border: '1px solid #e1e0db',
        borderRadius: 14,
        padding: 20,
      }}
    >
      {/* Panel header */}
      <div className="flex items-start justify-between gap-4 mb-4 flex-wrap">
        <div>
          <p className="text-eyebrow text-ink-40 mb-1">Постаматы</p>
          {/* Locker selector */}
          {locations.length > 1 ? (
            <select
              value={selectedId}
              onChange={e => setSelectedId(e.target.value)}
              className="font-bold bg-transparent border-none outline-none cursor-pointer"
              style={{ fontSize: 17, letterSpacing: '-0.01em', color: '#1a1a1a' }}
            >
              {locations.map(l => (
                <option key={l.id} value={l.id}>{l.name}</option>
              ))}
            </select>
          ) : (
            <h3 className="font-bold m-0" style={{ fontSize: 17, letterSpacing: '-0.01em' }}>{loc.name}</h3>
          )}
          <p className="mt-0.5 text-ink-40" style={{ fontSize: 13 }}>{loc.address}</p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="inline-flex items-center gap-1.5 font-bold rounded-full"
            style={{ padding: '5px 10px', background: '#EAF3ED', color: '#2E7D5B', fontSize: 12, borderRadius: 999 }}
          >
            <span
              className="rounded-full animate-pulse"
              style={{ width: 7, height: 7, background: '#2E7D5B', display: 'inline-block' }}
            />
            {freeCount}/{totalCount} свободно
          </span>
        </div>
      </div>

      {/* Cell grid */}
      <div
        className="grid gap-1.5 mb-3.5"
        style={{ gridTemplateColumns: `repeat(${Math.min(totalCount, 8)}, 1fr)` }}
      >
        {loc.units.map(unit => {
          const style = CELL_STYLE[unit.status] || CELL_STYLE.MAINTENANCE
          const isAvailable = unit.status === 'AVAILABLE'
          return (
            <div
              key={unit.id}
              onClick={() => handleUnitClick(loc.id, unit)}
              className="flex flex-col items-center justify-center font-bold transition-transform"
              style={{
                aspectRatio: '1',
                borderRadius: 8,
                border: `1px solid ${style.border}`,
                background: style.bg,
                color: style.color,
                cursor: isAvailable ? 'pointer' : 'default',
              }}
              onMouseEnter={e => { if (isAvailable) (e.currentTarget.style.transform = 'translateY(-2px)') }}
              onMouseLeave={e => { (e.currentTarget.style.transform = '') }}
              title={isAvailable
                ? `#${unit.unit_number} — Нажмите для создания набора`
                : `#${unit.unit_number} — ${style.label}`}
            >
              <span style={{ fontSize: 16, fontWeight: 700 }}>{unit.unit_number}</span>
              {unit.temperature != null && (
                <span style={{ fontSize: 10, fontWeight: 500, opacity: 0.7, marginTop: 1, fontVariantNumeric: 'tabular-nums' }}>
                  {unit.temperature}°C
                </span>
              )}
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div
        className="flex flex-wrap gap-3.5 pt-2.5"
        style={{ borderTop: '1px solid #ececea' }}
      >
        {Object.entries(CELL_STYLE).map(([key, s]) => (
          <span key={key} className="inline-flex items-center gap-1.5" style={{ fontSize: 12, color: '#4a4a4a' }}>
            <span className="rounded" style={{ width: 10, height: 10, background: LEGEND_DOTS[key] || s.bg, display: 'inline-block', borderRadius: 3 }} />
            {s.label}
          </span>
        ))}
      </div>

      <ConfirmModal
        open={!!confirmUnit}
        title="Создать набор?"
        message={confirmUnit
          ? `Вы выбрали ячейку #${confirmUnit.unit.unit_number} постамата ${loc?.name}. Перейти к созданию набора?`
          : ''}
        confirmText="Да, создать"
        onConfirm={handleConfirm}
        onCancel={() => setConfirmUnit(null)}
      />
    </section>
  )
}

// ── Combo status helpers ──────────────────────────────────────────────────────

const COMBO_STATUS: Record<string, { label: string; bg: string; color: string }> = {
  available: { label: 'В продаже',         bg: '#EAF3ED', color: '#2E7D5B' },
  reserved:  { label: 'Забронирован',      bg: '#FFF4DE', color: '#C88A1B' },
  sold:      { label: 'Продано',           bg: '#f7f6f3', color: '#4a4a4a' },
  pending:   { label: 'Ожидает размещения', bg: '#FFF4DE', color: '#C88A1B' },
}

const FILTER_TABS = ['Все', 'В продаже', 'Резерв', 'Завершено'] as const

// ── Main dashboard ────────────────────────────────────────────────────────────

export default function SellerDashboard() {
  const [shop, setShop] = useState<any>(null)
  const [locations, setLocations] = useState<LocationData[]>([])
  const [combos, setCombos] = useState<any[]>([])
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState<string>('Все')
  const [openMenuId, setOpenMenuId] = useState<string | null>(null)
  const [confirmCancelId, setConfirmCancelId] = useState<string | null>(null)
  const [cancellingId, setCancellingId] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    Promise.all([
      getMyShop().catch(() => null),
      getMyLockers().catch(() => ({ data: [] })),
      getMyCombos().catch(() => []),
      getSalesSummary().catch(() => null),
    ]).then(([s, l, c, sum]) => {
      const shopData = s?.data || s
      if (!shopData) { logout(); router.replace('/login'); return; }
      setShop(shopData)
      setLocations((l?.data || []).map((loc: any) => ({
        ...loc,
        units: (loc.units || []).map((u: any) => ({
          id: u.id,
          unit_number: u.unit_number,
          status: (u.status || 'AVAILABLE').toUpperCase(),
          is_active: u.is_active,
          temperature: u.temperature ?? null,
        })),
      })))
      setCombos(Array.isArray(c) ? c : c?.data || [])
      setSummary(sum?.data || sum)
      setLoading(false)
    })
  }, [])

  // Firebase realtime subscription
  useEffect(() => {
    if (locations.length === 0) return
    const unsubscribes: (() => void)[] = []
    try {
      const db = getFirestoreDb()
      for (const loc of locations) {
        const unitsRef = collection(db, 'locker_locations', loc.id, 'units')
        const unsub = onSnapshot(unitsRef, snapshot => {
          setLocations(prev => prev.map(prevLoc => {
            if (prevLoc.id !== loc.id) return prevLoc
            const updated = [...prevLoc.units]
            snapshot.docChanges().forEach(change => {
              const data = change.doc.data()
              const idx = updated.findIndex(u => u.id === change.doc.id)
              if (idx >= 0) {
                updated[idx] = { ...updated[idx], ...data, status: (data.status || updated[idx].status || 'AVAILABLE').toUpperCase() }
              } else if (change.type === 'added') {
                updated.push({ id: change.doc.id, unit_number: data.unit_number || 0, status: (data.status || 'AVAILABLE').toUpperCase(), is_active: data.is_active ?? true, ...data })
              }
            })
            updated.sort((a, b) => a.unit_number - b.unit_number)
            return { ...prevLoc, units: updated }
          }))
        }, err => console.warn('Firebase listener error:', err))
        unsubscribes.push(unsub)
      }
    } catch { console.warn('Firebase not available, using static data') }
    return () => unsubscribes.forEach(fn => fn())
  }, [locations.length])

  async function handleCancelCombo() {
    if (!confirmCancelId) return
    const id = confirmCancelId
    setConfirmCancelId(null)
    setCancellingId(id)
    try {
      await cancelCombo(id)
      setCombos(prev => prev.map(c => c.id === id ? { ...c, status: 'cancelled' } : c))
    } catch {} finally { setCancellingId(null) }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )

  const activeCount  = combos.filter((c: any) => c.status === 'available').length
  const soldCount    = combos.filter((c: any) => c.status === 'sold').length

  const filteredCombos = combos.filter((c: any) => {
    if (activeFilter === 'Все') return ['available', 'reserved', 'pending'].includes(c.status)
    if (activeFilter === 'В продаже') return c.status === 'available'
    if (activeFilter === 'Резерв') return c.status === 'reserved'
    if (activeFilter === 'Завершено') return c.status === 'sold'
    return true
  })

  return (
    <div className="flex flex-col gap-5" style={{ padding: '24px 32px 48px' }}>

      {/* KPI strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard
          icon={<Package size={16} strokeWidth={2} />}
          iconBg="#FFF8E1" iconColor="#8a6d00"
          value={activeCount}
          label="Активных наборов"
          trend={activeCount > 0 ? `+${activeCount}` : undefined}
          trendColor="eco"
        />
        <KpiCard
          icon={<CheckCircle2 size={16} strokeWidth={2} />}
          iconBg="#EAF3ED" iconColor="#2E7D5B"
          value={soldCount}
          label="Продано за всё время"
          trend={soldCount > 0 ? `+${soldCount}` : undefined}
          trendColor="eco"
        />
        <KpiCard
          icon={<TrendingUp size={16} strokeWidth={2} />}
          iconBg="#efece5" iconColor="#1a1a1a"
          value={summary?.total_revenue ? Math.round(summary.total_revenue).toLocaleString('ru') : '—'}
          unit={summary?.total_revenue ? '₽' : undefined}
          label="Общая выручка"
        />
        <KpiCard
          icon={<Leaf size={16} strokeWidth={2} />}
          iconBg="#EAF3ED" iconColor="#2E7D5B"
          value={summary?.co2_saved_kg ? summary.co2_saved_kg.toFixed(1) : '—'}
          unit={summary?.co2_saved_kg ? 'кг CO₂' : undefined}
          label="Сохранено в атмосфере"
          trend="↗ вклад"
          trendColor="eco"
        />
      </div>

      {/* Postamat panel */}
      {locations.length === 0 ? (
        <div
          className="text-center text-ink-40"
          style={{ background: '#fff', border: '1px solid #e1e0db', borderRadius: 14, padding: 32 }}
        >
          <p className="font-semibold">Нет привязанных постаматов</p>
          <p className="mt-1" style={{ fontSize: 13 }}>Обратитесь к администратору для привязки</p>
        </div>
      ) : (
        <PostamatPanel locations={locations} />
      )}

      {/* Active sets */}
      <section
        style={{
          background: '#ffffff',
          border: '1px solid #e1e0db',
          borderRadius: 14,
          padding: 20,
        }}
      >
        <div className="flex items-start justify-between gap-4 mb-4 flex-wrap">
          <div>
            <p className="text-eyebrow text-ink-40 mb-1">Активные наборы</p>
            <h3 className="font-bold m-0" style={{ fontSize: 17, letterSpacing: '-0.01em' }}>
              {activeCount} {activeCount === 1 ? 'набор' : activeCount < 5 ? 'набора' : 'наборов'} в продаже
            </h3>
          </div>
          {/* Segmented filter */}
          <div
            className="inline-flex gap-0.5 p-0.5"
            style={{ background: '#f7f6f3', borderRadius: 9 }}
          >
            {FILTER_TABS.map(tab => (
              <button
                key={tab}
                onClick={() => setActiveFilter(tab)}
                className="transition-all font-semibold"
                style={{
                  padding: '6px 12px',
                  borderRadius: 7,
                  fontSize: 12.5,
                  color: activeFilter === tab ? '#1a1a1a' : '#8a8a8a',
                  background: activeFilter === tab ? '#ffffff' : 'transparent',
                  boxShadow: activeFilter === tab ? '0 1px 2px rgba(20,20,20,.04), 0 0 0 1px rgba(20,20,20,.04)' : 'none',
                }}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {filteredCombos.length === 0 ? (
          <div className="py-10 text-center text-ink-40" style={{ fontSize: 14 }}>
            <Package size={32} className="mx-auto mb-3 opacity-30" />
            <p className="font-semibold">Нет наборов в этой категории</p>
            <Link href="/seller/add-item" className="inline-flex items-center gap-1.5 mt-3 font-bold"
              style={{ fontSize: 13, color: '#FFC629' }}>
              <Plus size={14} /> Добавить набор
            </Link>
          </div>
        ) : (
          <div>
            {filteredCombos.slice(0, 5).map((combo: any) => {
              const comboImg = combo.image ? imgUrl(combo.image) : null
              const productImg = combo.products?.find((p: any) => p.product_image)?.product_image
              const thumb = comboImg || (productImg ? imgUrl(productImg) : null)
              const st = COMBO_STATUS[combo.status] || COMBO_STATUS.available
              const soldQty = combo.sold_quantity ?? 0
              const totalQty = combo.total_quantity ?? combo.quantity ?? 1
              const pct = totalQty ? Math.round(soldQty / totalQty * 100) : 0
              const endTime = combo.sale_end_time
                ? new Date((combo.sale_end_time.endsWith('Z') ? combo.sale_end_time : combo.sale_end_time + 'Z'))
                    .toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })
                : null

              return (
                <div
                  key={combo.id}
                  className="grid items-center"
                  style={{
                    gridTemplateColumns: '56px 1fr auto 32px',
                    gap: 14,
                    padding: '14px 4px',
                    borderTop: '1px solid #ececea',
                  }}
                >
                  {/* Thumbnail */}
                  <div
                    className="flex-shrink-0 overflow-hidden"
                    style={{ width: 56, height: 56, borderRadius: 10, background: '#efece5' }}
                  >
                    {thumb ? (
                      <Image src={thumb} alt={combo.title} width={56} height={56}
                        className="object-cover w-full h-full" unoptimized />
                    ) : (
                      <div className="w-full h-full grid place-items-center">
                        <ShoppingBasket size={20} className="text-ink-40 opacity-50" />
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="font-bold truncate" style={{ fontSize: 15 }}>{combo.title}</span>
                      <span
                        className="font-bold rounded-full flex-shrink-0 whitespace-nowrap"
                        style={{ padding: '3px 9px', fontSize: 11.5, background: st.bg, color: st.color, borderRadius: 999 }}
                      >
                        {st.label}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5 flex-wrap" style={{ fontSize: 12, color: '#4a4a4a' }}>
                      <span className="font-bold">
                        {combo.sale_price} ₽{' '}
                        {combo.original_price && (
                          <s className="font-normal text-ink-40">{combo.original_price} ₽</s>
                        )}
                      </span>
                      {combo.locker_unit_number && (
                        <>
                          <span className="text-ink-40">·</span>
                          <span>Ячейка <b>{combo.locker_unit_number}</b></span>
                        </>
                      )}
                      {endTime && (
                        <>
                          <span className="text-ink-40">·</span>
                          <span>до {endTime}</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* More menu */}
                  <div className="relative">
                    <button
                      className="grid place-items-center transition-colors text-ink-40 rounded-lg"
                      style={{ width: 32, height: 32, borderRadius: 8, background: openMenuId === combo.id ? '#f7f6f3' : 'transparent', color: openMenuId === combo.id ? '#1a1a1a' : '#8a8a8a' }}
                      onClick={e => { e.stopPropagation(); setOpenMenuId(openMenuId === combo.id ? null : combo.id) }}
                      onMouseEnter={e => { (e.currentTarget.style.background = '#f7f6f3'); (e.currentTarget.style.color = '#1a1a1a') }}
                      onMouseLeave={e => { if (openMenuId !== combo.id) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#8a8a8a' } }}
                    >
                      <MoreHorizontal size={18} />
                    </button>
                    {openMenuId === combo.id && (
                      <div
                        className="absolute right-0 z-50 shadow-xl rounded-[12px] overflow-hidden"
                        style={{ top: 36, minWidth: 160, background: '#fff', border: '1px solid #e1e0db' }}
                        onClick={e => e.stopPropagation()}
                      >
                        <Link
                          href={`/seller/items/${combo.id}`}
                          className="flex items-center gap-2.5 px-4 py-2.5 text-sm font-semibold text-ink-100 hover:bg-line/60 transition-colors"
                          onClick={() => setOpenMenuId(null)}
                        >
                          Редактировать
                        </Link>
                        {combo.status === 'available' && (
                          <button
                            className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm font-semibold text-accent hover:bg-accent/10 transition-colors disabled:opacity-50"
                            disabled={cancellingId === combo.id}
                            onClick={() => { setOpenMenuId(null); setConfirmCancelId(combo.id) }}
                          >
                            {cancellingId === combo.id ? 'Отмена...' : 'Снять с продажи'}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* Close dropdown on outside click */}
      {openMenuId && (
        <div className="fixed inset-0 z-40" onClick={() => setOpenMenuId(null)} />
      )}

      <ConfirmModal
        open={!!confirmCancelId}
        title="Снять с продажи?"
        message="Набор будет снят с продажи и станет недоступен покупателям."
        confirmText="Да, снять"
        onConfirm={handleCancelCombo}
        onCancel={() => setConfirmCancelId(null)}
      />
    </div>
  )
}
