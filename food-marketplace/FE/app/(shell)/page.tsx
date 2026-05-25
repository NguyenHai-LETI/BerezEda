'use client'
import { useEffect, useState, useRef } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { MapPin, Lock, Navigation } from 'lucide-react'
import { getCombos, getLockers, getOrders } from '@/lib/api'
import { getUser } from '@/lib/auth'
import { API_URL } from '@/lib/constants'
import { CountdownBadge } from '@/components/CountdownBadge'
import { useI18n } from '@/contexts/I18nContext'
import type { Locale } from '@/lib/i18n'

interface UserPos { lat: number; lng: number }

const LOCALE_BCP: Record<Locale, string> = { ru: 'ru-RU', en: 'en-US', vi: 'vi-VN' }

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371
  const toRad = (d: number) => (d * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.asin(Math.sqrt(a))
}

export default function HomePage() {
  const [combos, setCombos] = useState<any[]>([])
  const [lockers, setLockers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [timeFilter, setTimeFilter] = useState<'today' | null>(null)
  const [discountFilter, setDiscountFilter] = useState<30 | 50 | 70 | null>(null)
  const [distFilter, setDistFilter] = useState<1 | 3 | 5 | null>(null)
  const [isSticky, setIsSticky] = useState(false)
  const sentinelRef = useRef<HTMLDivElement>(null)
  const [userPos, setUserPos] = useState<UserPos | null>(null)
  const [showAllCombos, setShowAllCombos] = useState(false)
  const [monthlyCompleted, setMonthlyCompleted] = useState(0)

  const MAX_COMBOS = 12
  const { t, locale } = useI18n()
  const user = getUser()

  useEffect(() => {
    async function load() {
      try {
        const now = new Date()
        const [c, l, o] = await Promise.all([
          getCombos(),
          getLockers(),
          getOrders(now.getFullYear(), now.getMonth() + 1),
        ])
        setCombos(c.data || [])
        setLockers(l.data || [])
        const orders: any[] = o?.data || []
        setMonthlyCompleted(orders.filter((x: any) => x.status === 'completed').length)
      } catch {}
      setLoading(false)
    }
    load()

    if (typeof navigator !== 'undefined' && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        pos => setUserPos({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        () => {},
        { timeout: 8000, maximumAge: 60000 }
      )
    }
  }, [])

  useEffect(() => {
    const el = sentinelRef.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => setIsSticky(!entry.isIntersecting),
      { threshold: 0 }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  function imgUrl(path?: string) {
    if (!path) return null
    if (path.startsWith('http')) return path
    const base = API_URL.replace(/\/api\/?$/, '')
    return `${base}/uploads/${path}`
  }

  function remainingSecs(saleEndTime?: string) {
    if (!saleEndTime) return 0
    const end = new Date(saleEndTime.endsWith('Z') ? saleEndTime : saleEndTime + 'Z')
    return Math.max(0, Math.floor((end.getTime() - Date.now()) / 1000))
  }

  function formatDist(km: number): string {
    if (km < 1) return t('home.dist_m').replace('{n}', String(Math.round(km * 1000)))
    return t('home.dist_km').replace('{n}', km.toFixed(1))
  }

  const bcpLocale = LOCALE_BCP[locale as Locale] ?? 'ru-RU'
  const todayDate = new Date().toLocaleDateString(bcpLocale, { day: 'numeric', month: 'long' })
  const todayLabel = `${t('home.today')}, ${todayDate}`

  const filteredCombos = combos.filter(c => {
    if (timeFilter === 'today') {
      const raw = c.sale_start_time ?? c.sale_end_time
      const start = raw ? new Date(raw.endsWith('Z') ? raw : raw + 'Z') : null
      if (!start) return false
      const now = new Date()
      if (!(start.getFullYear() === now.getFullYear() && start.getMonth() === now.getMonth() && start.getDate() === now.getDate())) return false
    }
    if (discountFilter !== null && (c.discount_rate ?? 0) < discountFilter) return false
    if (distFilter !== null && userPos) {
      if (c.locker_info?.locker_lat == null || c.locker_info?.locker_lng == null) return false
      if (haversineKm(userPos.lat, userPos.lng, c.locker_info.locker_lat, c.locker_info.locker_lng) > distFilter) return false
    }
    return true
  })

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-6 w-full">
      {/* Hero card */}
      <div className="rounded-card bg-gradient-to-br from-[#1a1a1a] to-[#2d2d2d] p-6 flex flex-col sm:flex-row sm:items-center gap-6">
        <div className="flex-1 min-w-0">
          <div className="text-[11px] font-semibold text-white/50 uppercase tracking-widest mb-1">{todayLabel}</div>
          <h2 className="text-xl font-extrabold text-white mb-2">
            {t('home.greeting').replace('{name}', user?.name || t('home.guest'))}
          </h2>
          <p className="text-sm text-white/70 leading-relaxed">
            {t('home.tagline')}
          </p>
        </div>
        <div className="bg-black/40 rounded-[14px] px-5 py-3 shrink-0 text-center">
          <div className="text-[10px] font-semibold text-white/40 uppercase tracking-widest mb-3">{t('home.this_month')}</div>
          <div className="flex items-center gap-5">
            <div className="text-center">
              <div className="text-2xl font-extrabold text-primary leading-none">{monthlyCompleted}</div>
              <div className="text-[11px] text-white/50 mt-1">{t('home.saved_count')}</div>
            </div>
            <div className="w-px h-8 bg-white/20" />
            <div className="text-center">
              <div className="text-2xl font-extrabold text-primary leading-none">{(monthlyCompleted * 0.15).toFixed(1)} кг</div>
              <div className="text-[11px] text-white/50 mt-1">{t('home.co2_saved')}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Sentinel for sticky detection */}
      <div ref={sentinelRef} className="h-px w-full -my-3" />

      {/* Combos panel */}
      <section className="bg-surface rounded-card shadow-sm">
        {/* Sticky filter bar */}
        <div className={`sticky top-[60px] z-20 bg-surface rounded-t-card transition-shadow ${isSticky ? 'shadow-md' : ''}`}>
          <div className="overflow-x-auto px-5 py-3 border-b border-line">
            <div className="flex items-center gap-2 min-w-max">
              {/* Group: Время */}
              <span className="text-[11px] font-semibold text-ink-40 uppercase tracking-wider shrink-0">Время</span>
              <button
                onClick={() => setTimeFilter(null)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
                  timeFilter === null ? 'bg-primary border-primary text-ink-100' : 'bg-surface border-line text-ink-60 hover:text-ink-100'
                }`}
              >
                {t('home.filter_all')}
              </button>
              <button
                onClick={() => setTimeFilter(prev => prev === 'today' ? null : 'today')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
                  timeFilter === 'today' ? 'bg-primary border-primary text-ink-100' : 'bg-surface border-line text-ink-60 hover:text-ink-100'
                }`}
              >
                {t('home.filter_today')}
              </button>

              <div className="w-px h-5 bg-line mx-1 shrink-0" />

              {/* Group: Скидка */}
              <span className="text-[11px] font-semibold text-ink-40 uppercase tracking-wider shrink-0">Скидка</span>
              {([30, 50, 70] as const).map(d => (
                <button
                  key={d}
                  onClick={() => setDiscountFilter(prev => prev === d ? null : d)}
                  className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
                    discountFilter === d ? 'bg-primary border-primary text-ink-100' : 'bg-surface border-line text-ink-60 hover:text-ink-100'
                  }`}
                >
                  ≥{d}%
                </button>
              ))}

              <div className="w-px h-5 bg-line mx-1 shrink-0" />

              {/* Group: Locker distance */}
              <span className="text-[11px] font-semibold text-ink-40 uppercase tracking-wider shrink-0">Locker</span>
              {([1, 3, 5] as const).map(d => (
                <button
                  key={d}
                  onClick={() => setDistFilter(prev => prev === d ? null : d)}
                  className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors border ${
                    distFilter === d ? 'bg-primary border-primary text-ink-100' : 'bg-surface border-line text-ink-60 hover:text-ink-100'
                  }`}
                >
                  &lt;{d} км
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="p-5 pt-4">
        <div className="flex items-center mb-4">
          <div>
            <div className="text-[11px] font-semibold text-ink-40 uppercase tracking-wider mb-0.5">{t('home.combos_section')}</div>
            <h3 className="text-base font-bold text-ink-100">
              {t('home.combos_subtitle').replace('{count}', String(filteredCombos.length))}
            </h3>
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {[1,2,3,4].map(i => <div key={i} className="rounded-card bg-line animate-pulse aspect-[4/3]" />)}
          </div>
        ) : filteredCombos.length === 0 ? (
          <div className="flex flex-col items-center py-12 text-ink-40 text-sm">
            <div className="text-3xl mb-3">🛒</div>
            <p className="font-medium">{t('home.empty_title')}</p>
            <p className="text-xs mt-1">{t('home.empty_sub')}</p>
          </div>
        ) : (
          <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {(showAllCombos ? filteredCombos : filteredCombos.slice(0, MAX_COMBOS)).map(combo => {
              const comboImg = combo.image ? imgUrl(combo.image) : null
              const productImg = combo.products?.find((p: any) => p.product_image)?.product_image
              const thumb = comboImg || (productImg ? imgUrl(productImg) : null)
              return (
                <Link key={combo.id} href={`/combos/${combo.id}`} className="group block">
                  <div className="rounded-card border border-line bg-surface hover:shadow-md transition-shadow overflow-hidden">
                    <div className="relative w-full aspect-[4/3]">
                      <div className="absolute inset-0 bg-line/50">
                        {thumb && (
                          <Image src={thumb} alt={combo.title} fill className="object-cover" unoptimized />
                        )}
                      </div>
                      <span
                        className="absolute top-2.5 left-2.5 text-[11px] font-bold px-2 py-0.5 rounded-full text-white"
                        style={{
                          background: combo.discount_rate >= 50
                            ? '#FF0022'
                            : combo.discount_rate >= 30
                              ? '#D85A30'
                              : '#EF9F27',
                        }}
                      >
                        −{combo.discount_rate}%
                      </span>
                      {combo.sale_end_time && (
                        <div className="absolute top-2.5 right-2.5">
                          <CountdownBadge seconds={remainingSecs(combo.sale_end_time)} className="bg-black/60 text-white text-[11px]" />
                        </div>
                      )}
                    </div>
                    <div className="p-3">
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className="w-2 h-2 rounded-full bg-eco shrink-0" />
                        {/* shop_name: user-generated, keep as-is */}
                        <span className="text-xs text-eco font-semibold truncate">{combo.shop_name}</span>
                        {combo.shop_rating != null && (
                          <span className="text-[11px] text-ink-40 ml-auto shrink-0">★ {combo.shop_rating}</span>
                        )}
                      </div>
                      {/* combo.title: user-generated, keep as-is */}
                      <div className="text-sm font-bold text-ink-100 truncate mb-1">{combo.title}</div>
                      <div className="flex items-baseline gap-1.5 mb-2">
                        <span className="text-base font-extrabold text-ink-100">{combo.sale_price?.toLocaleString(bcpLocale)} ₽</span>
                        <span className="text-xs text-ink-40 line-through">{combo.original_price?.toLocaleString(bcpLocale)} ₽</span>
                      </div>
                      {combo.locker_info && (
                        <div className="flex items-center justify-between gap-2 mt-1">
                          <div className="flex items-center gap-1 text-[11px] text-ink-40 min-w-0">
                            <MapPin className="h-3 w-3 shrink-0" />
                            {/* locker_name + locker_address: user-generated, keep as-is */}
                            <span className="truncate">
                              {combo.locker_info.locker_name}
                              {combo.locker_info.locker_address ? `, ${combo.locker_info.locker_address}` : ''}
                            </span>
                          </div>
                          {userPos && combo.locker_info.locker_lat != null && combo.locker_info.locker_lng != null && (
                            <div className="flex items-center gap-0.5 text-[11px] font-semibold text-primary shrink-0">
                              <Navigation className="h-2.5 w-2.5" />
                              <span>{formatDist(haversineKm(userPos.lat, userPos.lng, combo.locker_info.locker_lat, combo.locker_info.locker_lng))}</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>

          {/* More / Less button */}
          {filteredCombos.length > MAX_COMBOS && (
            <div className="flex justify-center mt-4">
              <button
                onClick={() => setShowAllCombos(prev => !prev)}
                className="px-5 py-2 rounded-full border border-line text-sm font-semibold text-ink-60 hover:text-ink-100 hover:border-ink-40 transition-colors"
              >
                {showAllCombos
                  ? t('home.show_less')
                  : t('home.show_more').replace('{n}', String(filteredCombos.length - MAX_COMBOS))}
              </button>
            </div>
          )}
          </>
        )}
        </div>
      </section>

      {/* Lockers panel */}
      <section className="bg-surface rounded-card shadow-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-[11px] font-semibold text-ink-40 uppercase tracking-wider mb-0.5">{t('home.lockers_section')}</div>
            <h3 className="text-base font-bold text-ink-100">{t('home.lockers_subtitle')}</h3>
          </div>
          <Link href="/map" className="text-sm font-semibold text-primary hover:text-primary-hover transition-colors">
            {t('home.view_map')}
          </Link>
        </div>

        {loading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {[1,2,3,4].map(i => <div key={i} className="rounded-card bg-line animate-pulse aspect-[4/3]" />)}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {lockers.slice(0, 8).map(loc => {
              const locImg = loc.image ? imgUrl(loc.image) : null
              const availSets = combos.filter(c => c.locker_location_id === loc.id).length
              return (
                <Link key={loc.id} href="/map" className="group block">
                  <div className="rounded-card border border-line bg-surface hover:shadow-md transition-shadow overflow-hidden">
                    <div className="relative w-full aspect-[4/3] bg-line/50 flex items-center justify-center">
                      {locImg ? (
                        <Image src={locImg} alt={loc.name} fill className="object-cover" unoptimized />
                      ) : (
                        <Lock className="h-8 w-8 text-line2" />
                      )}
                    </div>
                    <div className="p-3">
                      {/* loc.name + loc.address: user-generated, keep as-is */}
                      <div className="text-sm font-bold text-ink-100 truncate mb-0.5">{loc.name}</div>
                      <div className="text-xs text-ink-40 truncate mb-2">{loc.address}</div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-eco">
                          {t('home.combos_available').replace('{count}', String(availSets))}
                        </span>
                        <span className="text-xs text-ink-40">{loc.distance || ''}</span>
                      </div>
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
