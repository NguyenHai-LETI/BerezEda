'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import { MapPin, Clock, Heart, ArrowRight, Leaf, Plus, Minus } from 'lucide-react'
import { EmptyStateNoImage } from '@/components/EmptyStateNoImage'
import { routes } from '@/lib/routes'
import { getCombo, getFavoriteShops, addFavoriteShop, removeFavoriteShop } from '@/lib/api'
import { formatRUB } from '@/lib/format'
import { API_URL } from '@/lib/constants'

function fmtSecs(secs: number): string {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  return [h, m, s].map(n => String(n).padStart(2, '0')).join(':')
}

function calcEco(original: number, sale: number) {
  const saved = original - sale
  const foodG = Math.round(saved * 2.5)
  const co2 = +(foodG * 0.0025).toFixed(2)
  return { foodG, co2, km: Math.round(co2 / 0.21), bulb: Math.round(co2 / 0.05) }
}

function imgUrl(path?: string | null): string | null {
  if (!path) return null
  if (path.startsWith('http') || path.startsWith('blob:')) return path
  const base = API_URL.replace(/\/api\/?$/, '')
  return `${base}/uploads/${path}`
}

function remainingSecs(saleEndTime?: string | null): number {
  if (!saleEndTime) return 0
  const end = new Date(saleEndTime.endsWith('Z') ? saleEndTime : saleEndTime + 'Z')
  return Math.max(0, Math.floor((end.getTime() - Date.now()) / 1000))
}

export default function ItemDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [combo, setCombo] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [qty, setQty] = useState(1)
  const [fav, setFav] = useState(false)
  const [favId, setFavId] = useState<string | null>(null)
  const [favLoading, setFavLoading] = useState(false)
  const [countdown, setCountdown] = useState(0)

  useEffect(() => {
    getCombo(id).then((res: any) => {
      const data = res.data || res
      setCombo(data)
      setCountdown(remainingSecs(data.sale_end_time))
    }).catch(() => {}).finally(() => setLoading(false))

    getFavoriteShops().then((res: any) => {
      const favShops: any[] = res.data || []
      // We don't have shop_id directly until combo loads, check after
    }).catch(() => {})
  }, [id])

  useEffect(() => {
    if (!combo?.shop_id) return
    getFavoriteShops().then((res: any) => {
      const favShops: any[] = res.data || []
      const found = favShops.find((f: any) => f.shop_id === combo.shop_id || f.id === combo.shop_id)
      if (found) { setFav(true); setFavId(found.id || found.shop_id) }
    }).catch(() => {})
  }, [combo?.shop_id])

  useEffect(() => {
    if (countdown <= 0) return
    const timer = setInterval(() => setCountdown(s => Math.max(0, s - 1)), 1000)
    return () => clearInterval(timer)
  }, [countdown > 0])

  async function toggleFav() {
    if (!combo?.shop_id || favLoading) return
    setFavLoading(true)
    try {
      if (fav && favId) {
        await removeFavoriteShop(favId)
        setFav(false); setFavId(null)
      } else {
        const res: any = await addFavoriteShop(combo.shop_id)
        setFav(true)
        setFavId(res?.data?.id || combo.shop_id)
      }
    } catch {} finally { setFavLoading(false) }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )

  if (!combo) {
    return (
      <div className="p-4">
        <p className="text-muted">Товар не найден</p>
        <Link href={routes.home} className="text-primary hover:underline mt-4 inline-block">
          На главную
        </Link>
      </div>
    )
  }

  const comboThumb = combo.image ? imgUrl(combo.image) : null
  const productImg = combo.products?.find((p: any) => p.product_image)?.product_image
  const thumb = comboThumb || (productImg ? imgUrl(productImg) : null)
  const salePrice = combo.sale_price || 0
  const originalPrice = combo.original_price || salePrice
  const discountPct = combo.discount_rate || Math.round((1 - salePrice / originalPrice) * 100)
  const savedRub = originalPrice - salePrice
  const eco = calcEco(originalPrice, salePrice)
  const lockerInfo = combo.locker_info

  return (
    <div className="min-h-screen bg-bg">
      <section style={{ maxWidth: 1180, margin: '0 auto', padding: '28px 32px 160px' }}>
        <div className="grid gap-9 items-start grid-cols-1 lg:grid-cols-2">

          {/* Gallery */}
          <div className="lg:sticky" style={{ top: 84 }}>
            <div
              className="relative rounded-[14px] overflow-hidden bg-[#efece5]"
              style={{ aspectRatio: '4/3' }}
            >
              {thumb ? (
                <Image src={thumb} alt={combo.title} fill className="object-cover" sizes="(max-width:1024px) 100vw, 55vw" priority unoptimized />
              ) : (
                <EmptyStateNoImage size="lg" className="absolute inset-0 w-full h-full" />
              )}
              {discountPct > 0 && (
                <div
                  className="absolute font-extrabold text-sm text-white"
                  style={{ top: 14, left: 14, background: '#E8553D', padding: '7px 12px', borderRadius: 10, boxShadow: '0 4px 12px rgba(232,85,61,.3)' }}
                >
                  −{discountPct}%
                </div>
              )}
              <div
                className="absolute flex items-center gap-1.5 text-white font-semibold"
                style={{ top: 14, right: 14, background: 'rgba(20,20,20,.78)', padding: '7px 12px', borderRadius: 999, fontSize: 12.5, backdropFilter: 'blur(8px)' }}
              >
                <span className="rounded-full bg-primary" style={{ width: 7, height: 7, flexShrink: 0, boxShadow: '0 0 8px #FFC629' }} />
                В продаже
              </div>
            </div>

            {/* Product thumbnails */}
            {combo.products && combo.products.length > 0 && (
              <div className="grid grid-cols-4 gap-2 mt-2.5">
                {combo.products.slice(0, 4).map((p: any, i: number) => {
                  const pImg = p.product_image ? imgUrl(p.product_image) : null
                  return (
                    <div
                      key={p.id || i}
                      className="rounded-[10px] overflow-hidden bg-[#efece5]"
                      style={{ aspectRatio: '1/1', border: `2px solid ${i === 0 ? '#1a1a1a' : 'transparent'}` }}
                    >
                      {pImg ? (
                        <Image src={pImg} alt={p.product_name || ''} width={80} height={80} className="w-full h-full object-cover" unoptimized />
                      ) : (
                        <div className="w-full h-full bg-[#efece5]" />
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Info column */}
          <div className="flex flex-col gap-[18px]">

            {/* Restaurant row */}
            {combo.shop_name && (
              <div className="flex items-center gap-2.5 font-semibold text-ink-60" style={{ fontSize: 13.5 }}>
                <div className="flex-shrink-0 rounded-[6px]" style={{ width: 22, height: 22, background: 'linear-gradient(135deg,#FFC629,#f0a020)' }} />
                <Link href={combo.shop_id ? `/shops/${combo.shop_id}` : '#'} className="hover:underline underline-offset-2">
                  {combo.shop_name}
                </Link>
                {combo.shop_rating != null && (
                  <div className="flex items-center gap-1 text-ink-100 ml-1.5">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="#FFC629"><path d="M12 2l3 7 7 1-5 5 1 7-6-4-6 4 1-7-5-5 7-1z" /></svg>
                    <span>{Number(combo.shop_rating).toFixed(1)}</span>
                  </div>
                )}
              </div>
            )}

            {/* Title + favourite */}
            <div className="flex items-start gap-4">
              <h1 className="font-extrabold flex-1 m-0" style={{ fontSize: 32, lineHeight: 1.15, letterSpacing: '-0.02em' }}>
                {combo.title}
              </h1>
              <button
                onClick={toggleFav}
                disabled={favLoading}
                className="grid place-items-center flex-shrink-0 rounded-[12px] transition-colors disabled:opacity-50"
                style={{ width: 44, height: 44, background: '#f3f1ec' }}
                onMouseEnter={e => { e.currentTarget.style.background = '#e9e7e0' }}
                onMouseLeave={e => { e.currentTarget.style.background = '#f3f1ec' }}
                aria-label={fav ? 'Убрать из избранного' : 'В избранное'}
              >
                <Heart size={22} strokeWidth={1.8} style={{ fill: fav ? '#E8553D' : 'none', stroke: fav ? '#E8553D' : '#1a1a1a' }} />
              </button>
            </div>

            {/* Description */}
            {combo.description && (
              <p className="m-0 text-ink-60" style={{ fontSize: 15.5, lineHeight: 1.5 }}>{combo.description}</p>
            )}

            {/* Price row */}
            <div className="flex items-baseline gap-3.5 flex-wrap">
              <span className="font-extrabold" style={{ fontSize: 36, letterSpacing: '-0.02em', color: '#1a1a1a' }}>
                {formatRUB(salePrice * qty)}
              </span>
              <span className="font-medium" style={{ fontSize: 18, color: '#b0b0b0', textDecoration: 'line-through' }}>
                {formatRUB(originalPrice * qty)}
              </span>
              {savedRub > 0 && (
                <span className="font-bold" style={{ fontSize: 13.5, color: '#2E7D5B', background: '#EAF3ED', padding: '4px 10px', borderRadius: 999 }}>
                  экономия {formatRUB(savedRub)}
                </span>
              )}
            </div>

            {/* Pickup card */}
            {lockerInfo && (
              <div style={{ background: '#ffffff', border: '1px solid #e1e0db', borderRadius: 14, padding: 18 }}>
                <div className="grid grid-cols-2 gap-4">
                  {combo.sale_end_time && (
                    <div className="flex gap-2.5">
                      <Clock size={18} strokeWidth={1.7} className="flex-shrink-0 text-ink-60" style={{ marginTop: 1 }} />
                      <div>
                        <div className="font-bold uppercase text-ink-40" style={{ fontSize: 12, letterSpacing: '0.04em', marginBottom: 4 }}>Окно самовывоза</div>
                        <div className="font-bold text-ink-100" style={{ fontSize: 15, lineHeight: 1.3 }}>Сегодня</div>
                        <div className="text-ink-60" style={{ fontSize: 13, marginTop: 2 }}>
                          до {new Date(combo.sale_end_time.endsWith('Z') ? combo.sale_end_time : combo.sale_end_time + 'Z').toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                    </div>
                  )}
                  <div className="flex gap-2.5">
                    <MapPin size={18} strokeWidth={1.7} className="flex-shrink-0 text-ink-60" style={{ marginTop: 1 }} />
                    <div>
                      <div className="font-bold uppercase text-ink-40" style={{ fontSize: 12, letterSpacing: '0.04em', marginBottom: 4 }}>Адрес</div>
                      <div className="font-bold text-ink-100" style={{ fontSize: 15, lineHeight: 1.3 }}>{lockerInfo.locker_name}</div>
                      {lockerInfo.locker_address && (
                        <div className="text-ink-60" style={{ fontSize: 13, marginTop: 2 }}>
                          {lockerInfo.locker_address}{lockerInfo.unit_number != null ? ` · ячейка #${lockerInfo.unit_number}` : ''}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                {countdown > 0 && (
                  <>
                    <div style={{ height: 1, background: '#ececea', margin: '14px 0 12px' }} />
                    <div className="flex items-center gap-2 font-semibold rounded-[10px]" style={{ background: '#FFF8E1', padding: '10px 14px', fontSize: 13.5, color: '#8a6d00' }}>
                      <Clock size={16} strokeWidth={2} />
                      <span>До конца продажи: <b className="font-mono" style={{ color: '#6b5300', fontVariantNumeric: 'tabular-nums' }}>{fmtSecs(countdown)}</b></span>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Eco card */}
            <div style={{ background: 'linear-gradient(135deg,#f0f7f2,#e8f1ec)', border: '1px solid #d4e6dc', borderRadius: 14, padding: 18 }}>
              <div className="flex items-center gap-2.5 mb-3.5">
                <div className="grid place-items-center rounded-[8px]" style={{ width: 32, height: 32, background: '#2E7D5B' }}>
                  <Leaf size={18} strokeWidth={2} color="white" />
                </div>
                <span className="font-bold" style={{ fontSize: 15, color: '#2E7D5B' }}>Вклад в экологию</span>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="font-extrabold" style={{ fontSize: 22, letterSpacing: '-0.01em', color: '#1a1a1a' }}>{eco.foodG} г</div>
                  <div style={{ fontSize: 12.5, color: '#4a4a4a', marginTop: 2 }}>спасено от выброса</div>
                </div>
                <div>
                  <div className="font-extrabold" style={{ fontSize: 22, letterSpacing: '-0.01em', color: '#1a1a1a' }}>{eco.co2.toFixed(2)} кг</div>
                  <div style={{ fontSize: 12.5, color: '#4a4a4a', marginTop: 2 }}>CO₂ не попадёт в атмосферу</div>
                </div>
              </div>
              <p style={{ margin: '14px 0 0', paddingTop: 12, borderTop: '1px dashed #c4ddce', fontSize: 13, color: '#4a4a4a' }}>
                ≈ как <b style={{ color: '#2E7D5B' }}>{eco.km} км</b> поездки на машине или <b style={{ color: '#2E7D5B' }}>{eco.bulb} ч</b> работы лампочки
              </p>
            </div>

            {/* Composition */}
            {combo.products && combo.products.length > 0 && (
              <div>
                <h2 className="font-bold" style={{ fontSize: 17, margin: '6px 0 12px' }}>Что внутри</h2>
                <div style={{ background: '#ffffff', border: '1px solid #e1e0db', borderRadius: 14, overflow: 'hidden' }}>
                  {combo.products.map((p: any, idx: number) => {
                    const pImg = p.product_image ? imgUrl(p.product_image) : null
                    return (
                      <div
                        key={p.id || idx}
                        className="grid items-center"
                        style={{ gridTemplateColumns: '56px 1fr auto', gap: 14, padding: '14px 16px', borderTop: idx > 0 ? '1px solid #ececea' : 'none' }}
                      >
                        <div className="rounded-[10px] overflow-hidden bg-[#efece5] flex-shrink-0" style={{ width: 56, height: 56 }}>
                          {pImg ? (
                            <Image src={pImg} alt={p.product_name || ''} width={56} height={56} className="w-full h-full object-cover" unoptimized />
                          ) : (
                            <div className="w-full h-full bg-[#efece5]" />
                          )}
                        </div>
                        <div>
                          <div className="font-semibold text-ink-100" style={{ fontSize: 15 }}>{p.product_name || 'Продукт'}</div>
                          {p.price_at_time != null && (
                            <div className="text-ink-40" style={{ fontSize: 13, marginTop: 2 }}>{formatRUB(p.price_at_time)}</div>
                          )}
                        </div>
                        <div className="font-semibold text-ink-60" style={{ fontSize: 14 }}>×{p.quantity || 1}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Sticky CTA bar */}
      <div
        className="fixed z-20 left-4 right-4 lg:left-[272px]"
        style={{
          bottom: 18,
          background: '#ffffff',
          border: '1px solid #e1e0db',
          borderRadius: 16,
          padding: '12px 14px 12px 20px',
          display: 'grid',
          gridTemplateColumns: '1fr auto auto',
          gap: 16,
          alignItems: 'center',
          boxShadow: '0 12px 40px rgba(20,20,20,.12), 0 0 0 1px rgba(20,20,20,.03)',
        }}
      >
        <div>
          <div className="flex items-baseline gap-2.5">
            <span className="font-extrabold" style={{ fontSize: 22, letterSpacing: '-0.01em' }}>{formatRUB(salePrice * qty)}</span>
            <span className="font-medium" style={{ fontSize: 14, color: '#b0b0b0', textDecoration: 'line-through' }}>{formatRUB(originalPrice * qty)}</span>
          </div>
          <div className="font-semibold" style={{ fontSize: 12.5, color: '#2E7D5B' }}>В продаже · забронируйте сейчас</div>
        </div>

        {/* Qty stepper */}
        <div className="inline-flex items-center rounded-[12px] p-1" style={{ background: '#f3f1ec' }}>
          <button
            onClick={() => setQty(q => Math.max(1, q - 1))}
            className="grid place-items-center rounded-[8px] font-bold text-ink-60 transition-colors"
            style={{ width: 32, height: 32 }}
            onMouseEnter={e => { e.currentTarget.style.background = 'white'; e.currentTarget.style.color = '#1a1a1a' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#4a4a4a' }}
            aria-label="Уменьшить"
          >
            <Minus size={14} strokeWidth={2.5} />
          </button>
          <span className="font-bold font-mono text-center" style={{ minWidth: 28, fontVariantNumeric: 'tabular-nums' }}>{qty}</span>
          <button
            onClick={() => setQty(q => q + 1)}
            className="grid place-items-center rounded-[8px] font-bold text-ink-60 transition-colors"
            style={{ width: 32, height: 32 }}
            onMouseEnter={e => { e.currentTarget.style.background = 'white'; e.currentTarget.style.color = '#1a1a1a' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#4a4a4a' }}
            aria-label="Увеличить"
          >
            <Plus size={14} strokeWidth={2.5} />
          </button>
        </div>

        {/* Buy button */}
        <Link
          href={routes.checkout(combo.id)}
          className="inline-flex items-center gap-2 font-extrabold transition-shadow"
          style={{ background: '#FFC629', color: '#1a1a1a', padding: '12px 28px', borderRadius: 12, fontSize: 15.5, letterSpacing: '-0.005em' }}
          onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 6px 18px rgba(255,198,41,.5)' }}
          onMouseLeave={e => { e.currentTarget.style.boxShadow = 'none' }}
        >
          Забронировать <ArrowRight size={16} strokeWidth={2.2} />
        </Link>
      </div>
    </div>
  )
}
