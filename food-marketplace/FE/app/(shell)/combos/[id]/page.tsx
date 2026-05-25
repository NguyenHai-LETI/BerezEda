'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Heart, MapPin, Clock, Recycle, ShoppingBasket, UtensilsCrossed } from 'lucide-react'
import { getCombo, getFavoriteShops, addFavoriteShop, removeFavoriteShop, getShopReviews } from '@/lib/api'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/api\/?$/, '')

function buildImgUrl(path: string | null | undefined): string | null {
  if (!path) return null
  return path.startsWith('http') ? path : `${API_BASE}/uploads/${path.replace(/^\//, '')}`
}

function formatTime(dt: string | null | undefined): string {
  if (!dt) return ''
  const d = new Date(dt.endsWith('Z') ? dt : dt + 'Z')
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

function pluralReviews(n: number) {
  if (n % 10 === 1 && n % 100 !== 11) return `${n} отзыв`
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return `${n} отзыва`
  return `${n} отзывов`
}

function Stars({ rating, size = 14 }: { rating: number; size?: number }) {
  return (
    <span className="inline-flex gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <svg key={i} width={size} height={size} viewBox="0 0 24 24"
          fill={i <= Math.round(rating) ? '#FFC629' : 'none'}
          stroke={i <= Math.round(rating) ? '#FFC629' : '#d1d5db'}
          strokeWidth="1.5">
          <path d="M12 2l3 7 7 1-5 5 1 7-6-4-6 4 1-7-5-5 7-1z" />
        </svg>
      ))}
    </span>
  )
}

function CountdownTimer({ endTime }: { endTime: string }) {
  const calcSecs = () => {
    const end = new Date(endTime.endsWith('Z') ? endTime : endTime + 'Z').getTime()
    return Math.max(0, Math.floor((end - Date.now()) / 1000))
  }
  const [secs, setSecs] = useState(calcSecs)
  useEffect(() => {
    const t = setInterval(() => setSecs(calcSecs()), 1000)
    return () => clearInterval(t)
  }, [endTime])
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  const f = (n: number) => String(n).padStart(2, '0')
  return <b className="tabular-nums">{f(h)}:{f(m)}:{f(s)}</b>
}

export default function ComboDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [combo, setCombo] = useState<any>(null)
  const [reviews, setReviews] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [isFavoriteShop, setIsFavoriteShop] = useState(false)
  const [togglingFav, setTogglingFav] = useState(false)
  const [activeImg, setActiveImg] = useState(0)
  const [previewImg, setPreviewImg] = useState<string | null>(null)

  useEffect(() => {
    getCombo(id)
      .then(r => {
        const c = r.data
        setCombo(c)
        if (c?.shop_id) {
          Promise.all([
            getFavoriteShops().catch(() => ({ data: [] })),
            getShopReviews(c.shop_id).catch(() => ({ data: [] })),
          ]).then(([favRes, revRes]) => {
            const favs = favRes.data || []
            setIsFavoriteShop(favs.some((f: any) => f.id === c.shop_id || f.shop_id === c.shop_id))
            setReviews((revRes.data || []).slice(0, 3))
          })
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  async function toggleFavoriteShop() {
    if (!combo?.shop_id || togglingFav) return
    setTogglingFav(true)
    try {
      if (isFavoriteShop) { await removeFavoriteShop(combo.shop_id); setIsFavoriteShop(false) }
      else { await addFavoriteShop(combo.shop_id); setIsFavoriteShop(true) }
    } catch {}
    setTogglingFav(false)
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )
  if (!combo) return <div className="p-4 text-center text-gray-500">Набор не найден</div>

  const weight = combo.weight_grams || 0
  const co2 = weight * 2.5 / 1000
  const kmEquiv = Math.round(co2 / 0.21)
  const bulbHours = Math.round(co2 / 0.05)
  const isAvailable = combo.status === 'available'
  const salePrice = combo.sale_price || 0
  const originalPrice = combo.original_price || 0
  const discountRate = combo.discount_rate || 0
  const avgRating = combo.shop_avg_rating || 0
  const totalReviews = combo.shop_total_reviews || 0

  // Build image list: combo image first, then product images
  const allImages: string[] = []
  const comboImgUrl = buildImgUrl(combo.image)
  if (comboImgUrl) allImages.push(comboImgUrl)
  for (const p of (combo.products || [])) {
    const url = buildImgUrl(p.product_image)
    if (url && !allImages.includes(url)) allImages.push(url)
  }
  const currentImg = allImages[activeImg] || null

  const hasPickup = combo.sale_end_time || combo.locker_info?.locker_address
  const endMs = combo.sale_end_time
    ? new Date(combo.sale_end_time.endsWith('Z') ? combo.sale_end_time : combo.sale_end_time + 'Z').getTime()
    : 0

  return (
    <div className="relative min-h-screen bg-bg">
      {/* Lightbox */}
      {previewImg && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setPreviewImg(null)}>
          <img src={previewImg} alt="" className="max-w-full max-h-full rounded-xl object-contain" onClick={e => e.stopPropagation()} />
          <button className="absolute top-4 right-4 text-white text-3xl leading-none" onClick={() => setPreviewImg(null)}>×</button>
        </div>
      )}

      {/* Content */}
      <div className="max-w-[1180px] mx-auto px-4 sm:px-6 py-7 pb-36">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-9 items-start">

          {/* ── GALLERY ── */}
          <div className="lg:sticky lg:top-[72px]">
            <div className="relative aspect-[4/3] rounded-2xl overflow-hidden bg-stone-100 shadow-sm">
              {currentImg ? (
                <img
                  src={currentImg}
                  alt={combo.title}
                  className="w-full h-full object-cover cursor-zoom-in"
                  onClick={() => setPreviewImg(currentImg)}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <ShoppingBasket className="h-16 w-16 text-gray-300" />
                </div>
              )}
              {discountRate > 0 && (
                <div className="absolute top-3 left-3 bg-[#E8553D] text-white font-bold text-sm px-3 py-1.5 rounded-xl shadow-md">
                  -{discountRate}%
                </div>
              )}
              <div className={`absolute top-3 right-3 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold backdrop-blur-sm ${isAvailable ? 'bg-black/70 text-white' : 'bg-gray-500/70 text-white'}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${isAvailable ? 'bg-[#FFC629] shadow-[0_0_6px_#FFC629]' : 'bg-gray-400'}`} />
                {isAvailable ? 'Доступно' : 'Недоступно'}
              </div>
            </div>
            {allImages.length > 1 && (
              <div className="grid grid-cols-4 gap-2 mt-2.5">
                {allImages.slice(0, 4).map((url, i) => (
                  <button
                    key={i}
                    onClick={() => setActiveImg(i)}
                    className={`aspect-square rounded-xl overflow-hidden border-2 transition ${activeImg === i ? 'border-gray-900' : 'border-transparent opacity-70 hover:opacity-100'}`}
                  >
                    <img src={url} alt="" className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* ── INFO ── */}
          <div className="flex flex-col gap-5">
            {/* Shop + rating */}
            {combo.shop_name && (
              <div className="flex items-center gap-2 text-sm font-semibold text-gray-500 flex-wrap">
                <div className="w-5 h-5 rounded-md bg-gradient-to-br from-yellow-400 to-yellow-500 flex-shrink-0" />
                <Link href={combo.shop_id ? `/shops/${combo.shop_id}` : '#'} className="hover:underline underline-offset-2 text-gray-700">
                  {combo.shop_name}
                </Link>
                {avgRating > 0 && (
                  <span className="flex items-center gap-1 text-gray-900 ml-1">
                    <Stars rating={avgRating} size={13} />
                    <span className="font-bold">{avgRating.toFixed(1)}</span>
                  </span>
                )}
              </div>
            )}

            {/* Title + favourite */}
            <div className="flex gap-4 items-start">
              <h1 className="text-[28px] lg:text-[32px] font-extrabold text-gray-900 tracking-tight leading-tight flex-1">
                {combo.title}
              </h1>
              <button
                onClick={toggleFavoriteShop}
                disabled={togglingFav}
                className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 transition ${isFavoriteShop ? 'bg-red-50' : 'bg-gray-100 hover:bg-gray-200'}`}
                aria-label={isFavoriteShop ? 'Убрать из избранного' : 'В избранное'}
              >
                <Heart className={`h-5 w-5 transition ${isFavoriteShop ? 'fill-red-500 text-red-500' : 'text-gray-600'}`} />
              </button>
            </div>

            {combo.description && (
              <p className="text-[15px] text-gray-500 leading-relaxed -mt-2">{combo.description}</p>
            )}

            {/* Prices */}
            <div className="flex items-baseline gap-3 flex-wrap">
              <span className="text-[34px] font-extrabold text-gray-900 tracking-tight leading-none">
                {salePrice.toLocaleString('ru-RU')} ₽
              </span>
              {originalPrice > salePrice && (
                <>
                  <span className="text-lg text-gray-400 line-through">{originalPrice.toLocaleString('ru-RU')} ₽</span>
                  <span className="text-xs font-bold text-[#2E7D5B] bg-[#EAF3ED] px-2.5 py-1 rounded-full">
                    экономия {(originalPrice - salePrice).toLocaleString('ru-RU')} ₽
                  </span>
                </>
              )}
            </div>

            {/* Pickup card */}
            {hasPickup && (
              <div className="bg-white border border-gray-200 rounded-2xl p-4 space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  {combo.sale_end_time && (
                    <div className="flex gap-2.5">
                      <Clock className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-[10px] font-bold tracking-widest text-gray-400 uppercase mb-1">Окно выдачи</p>
                        <p className="text-sm font-bold text-gray-900">
                          {combo.sale_start_time ? formatTime(combo.sale_start_time) + ' – ' : ''}
                          {formatTime(combo.sale_end_time)}
                        </p>
                        <p className="text-xs text-gray-400 mt-0.5">забрать до конца продажи</p>
                      </div>
                    </div>
                  )}
                  {combo.locker_info?.locker_address && (
                    <div className="flex gap-2.5">
                      <MapPin className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-[10px] font-bold tracking-widest text-gray-400 uppercase mb-1">Адрес</p>
                        <p className="text-sm font-bold text-gray-900 leading-tight">
                          {combo.locker_info.locker_name || 'Постамат'}
                          {combo.locker_info.unit_number ? ` · №${combo.locker_info.unit_number}` : ''}
                        </p>
                        <p className="text-xs text-gray-400 mt-0.5">{combo.locker_info.locker_address}</p>
                      </div>
                    </div>
                  )}
                </div>
                {endMs > Date.now() && (
                  <div className="bg-[#FFF8E1] rounded-xl px-3 py-2.5 flex items-center gap-2 text-[13px] font-semibold text-amber-700">
                    <Clock className="h-3.5 w-3.5 flex-shrink-0" />
                    <span>До конца продажи: <CountdownTimer endTime={combo.sale_end_time} /></span>
                  </div>
                )}
              </div>
            )}

            {/* Eco card */}
            {weight > 0 && (
              <div className="bg-gradient-to-br from-[#f0f7f2] to-[#e8f1ec] border border-[#d4e6dc] rounded-2xl p-4">
                <div className="flex items-center gap-2.5 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-[#2E7D5B] flex items-center justify-center flex-shrink-0">
                    <Recycle className="h-4 w-4 text-white" />
                  </div>
                  <span className="font-bold text-[15px] text-[#2E7D5B]">Вклад в экологию</span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-[22px] font-extrabold text-gray-900 leading-none">{weight.toLocaleString('ru-RU')} г</p>
                    <p className="text-xs text-gray-500 mt-1">спасено от выброса</p>
                  </div>
                  <div>
                    <p className="text-[22px] font-extrabold text-gray-900 leading-none">{co2.toFixed(2)} кг</p>
                    <p className="text-xs text-gray-500 mt-1">CO₂ не попадёт в атмосферу</p>
                  </div>
                </div>
                {(kmEquiv > 0 || bulbHours > 0) && (
                  <div className="mt-3 pt-3 border-t border-dashed border-[#c4ddce] text-xs text-gray-500">
                    ≈ как <span className="font-semibold text-[#2E7D5B]">{kmEquiv} км</span> поездки на машине или{' '}
                    <span className="font-semibold text-[#2E7D5B]">{bulbHours} ч</span> работы лампочки
                  </div>
                )}
              </div>
            )}

            {/* Composition */}
            {combo.products?.length > 0 && (
              <div>
                <h2 className="text-[17px] font-bold text-gray-900 mb-3">Состав набора</h2>
                <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
                  {combo.products.map((p: any, i: number) => {
                    const pSrc = buildImgUrl(p.product_image)
                    return (
                      <div key={i} className={`flex items-center gap-3.5 px-4 py-3.5 ${i > 0 ? 'border-t border-gray-100' : ''}`}>
                        <div className="w-14 h-14 rounded-xl bg-stone-100 overflow-hidden flex-shrink-0">
                          {pSrc ? (
                            <img src={pSrc} alt={p.product_name || ''} className="w-full h-full object-cover cursor-zoom-in" onClick={() => setPreviewImg(pSrc)} />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <UtensilsCrossed className="h-5 w-5 text-gray-300" />
                            </div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-gray-800">{p.product_name || `Товар #${i + 1}`}</p>
                          <p className="text-xs text-gray-400 mt-0.5">Количество: {p.quantity}</p>
                        </div>
                        <span className="text-sm font-semibold text-gray-400 flex-shrink-0">×{p.quantity}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── REVIEWS ── */}
        {(reviews.length > 0 || avgRating > 0) && (
          <div className="mt-10">
            <div className="bg-white border border-gray-200 rounded-2xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  {avgRating > 0 ? (
                    <>
                      <span className="text-[28px] font-extrabold text-gray-900 tracking-tight leading-none">{avgRating.toFixed(1)}</span>
                      <div>
                        <Stars rating={avgRating} size={15} />
                        <p className="text-xs text-gray-400 mt-1">{pluralReviews(totalReviews)}</p>
                      </div>
                    </>
                  ) : (
                    <h2 className="text-[17px] font-bold text-gray-900">Отзывы</h2>
                  )}
                </div>
              </div>
              {reviews.length > 0 ? (
                <div>
                  {reviews.map((rev: any, i: number) => (
                    <div key={rev.id} className={`py-3 ${i > 0 ? 'border-t border-gray-100' : ''}`}>
                      <div className="flex items-center gap-2.5 mb-1.5">
                        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-yellow-400 to-yellow-500 flex items-center justify-center text-xs font-bold text-gray-900 flex-shrink-0">
                          {(rev.customer_id || 'U')[0].toUpperCase()}
                        </div>
                        <div className="flex-1">
                          <Stars rating={rev.rating} size={12} />
                        </div>
                        <span className="text-xs text-gray-400 flex-shrink-0">
                          {new Date(rev.created_at.endsWith('Z') ? rev.created_at : rev.created_at + 'Z').toLocaleDateString('ru-RU')}
                        </span>
                      </div>
                      {rev.comment && <p className="text-sm text-gray-500 leading-relaxed ml-9">{rev.comment}</p>}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">Отзывов пока нет</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── STICKY CTA ── */}
      <div className="fixed bottom-20 md:bottom-4 left-0 right-0 z-20 px-4 lg:left-64">
        <div className="max-w-[1180px] mx-auto">
          <div className="bg-white border border-gray-200 rounded-2xl px-5 py-3 flex items-center justify-between gap-4 shadow-xl">
            <div>
              <div className="flex items-baseline gap-2.5">
                <span className="text-[22px] font-extrabold text-gray-900 leading-none">{salePrice.toLocaleString('ru-RU')} ₽</span>
                {originalPrice > salePrice && (
                  <span className="text-sm text-gray-400 line-through">{originalPrice.toLocaleString('ru-RU')} ₽</span>
                )}
              </div>
              {isAvailable && (
                <p className="text-xs text-[#2E7D5B] font-semibold mt-0.5">Доступно · забрать до конца продажи</p>
              )}
            </div>
            {isAvailable ? (
              <button
                onClick={() => router.push(`/checkout/${id}`)}
                className="bg-[#FFC629] hover:bg-yellow-400 text-gray-900 font-bold py-3 px-7 rounded-xl text-[15px] transition flex items-center gap-2 hover:shadow-[0_6px_18px_rgba(255,198,41,0.5)] flex-shrink-0"
              >
                Купить
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
              </button>
            ) : (
              <div className="bg-gray-200 text-gray-500 font-bold py-3 px-7 rounded-xl text-[15px] flex-shrink-0">
                Недоступно
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
