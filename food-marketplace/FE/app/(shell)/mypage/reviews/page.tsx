'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Package, Star, ChevronRight, PenLine } from 'lucide-react'
import { getOrders } from '@/lib/api'
import { routes } from '@/lib/routes'
import { API_URL } from '@/lib/constants'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

function imgUrl(path?: string | null): string | null {
  if (!path) return null
  if (path.startsWith('http')) return path
  const base = API_URL.replace(/\/api\/?$/, '')
  return `${base}/uploads/${path.replace(/^\//, '')}`
}

function StarRow({ rating, size = 14 }: { rating: number; size?: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map(n => (
        <Star
          key={n}
          size={size}
          strokeWidth={1.5}
          style={{
            fill: n <= rating ? '#FFC629' : 'none',
            stroke: n <= rating ? '#FFC629' : '#d0cec7',
          }}
        />
      ))}
    </div>
  )
}

interface Order {
  id: string
  combo_id?: string
  shop_id?: string
  amount?: number
  status: string
  created_at: string
}

interface ReviewData {
  rating: number
  comment?: string
}

export default function ReviewsPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [reviews, setReviews] = useState<Record<string, ReviewData | null>>({})
  const [combos, setCombos] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [loadingReviews, setLoadingReviews] = useState(false)

  useEffect(() => {
    getOrders()
      .then(async (res: any) => {
        const all: Order[] = res.data || []
        const completed = all.filter(o => o.status === 'completed')
        setOrders(completed)
        setLoading(false)

        if (completed.length === 0) return

        // getOrders() already handled any token refresh via request().
        // Read the fresh token ONCE here — then use raw fetch for all concurrent
        // sub-requests so we never trigger a second concurrent refresh cycle.
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

        setLoadingReviews(true)
        const [comboEntries, reviewEntries] = await Promise.all([
          // Combos are public — no auth needed
          Promise.all(
            completed.map(async o => {
              if (!o.combo_id) return [o.combo_id ?? o.id, null] as const
              try {
                const r = await fetch(`${BASE}/combos/${o.combo_id}`)
                if (!r.ok) return [o.combo_id, null] as const
                const json = await r.json()
                return [o.combo_id, json.data ?? json] as const
              } catch {
                return [o.combo_id, null] as const
              }
            })
          ),
          // Reviews require auth — use the pre-read fresh token, no redirect risk
          Promise.all(
            completed.map(async o => {
              try {
                const r = await fetch(`${BASE}/reviews/order/${o.id}`, {
                  headers: token ? { Authorization: `Bearer ${token}` } : {},
                })
                if (!r.ok) return [o.id, null] as const
                const json = await r.json()
                const d = json?.data
                if (d && typeof d === 'object' && typeof d.rating === 'number') {
                  return [o.id, { rating: d.rating, comment: d.comment ?? undefined }] as const
                }
                return [o.id, null] as const
              } catch {
                return [o.id, null] as const
              }
            })
          ),
        ])

        setCombos(Object.fromEntries(comboEntries.filter(([id]) => id)))
        setReviews(Object.fromEntries(reviewEntries))
        setLoadingReviews(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )

  const reviewedCount = Object.values(reviews).filter(r => r !== null).length

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-4 max-w-[640px] mx-auto w-full">

      {orders.length === 0 ? (
        <div className="bg-surface rounded-card shadow-sm p-12 flex flex-col items-center gap-3 text-center">
          <Package className="h-10 w-10 text-line2" />
          <p className="font-semibold text-ink-60">Нет завершённых заказов</p>
          <p className="text-sm text-ink-40">Отзывы можно оставить после получения набора</p>
          <Link href="/" className="mt-2 text-sm font-semibold text-primary hover:underline">
            Найти наборы
          </Link>
        </div>
      ) : (
        <>
          {/* Summary */}
          <div className="flex items-center gap-4">
            <div className="flex-1 bg-surface rounded-card shadow-sm p-4 text-center">
              <div className="text-2xl font-extrabold text-ink-100 leading-none">{orders.length}</div>
              <div className="text-xs text-ink-40 mt-1">покупок</div>
            </div>
            <div className="flex-1 bg-surface rounded-card shadow-sm p-4 text-center">
              <div className="text-2xl font-extrabold text-eco leading-none">{reviewedCount}</div>
              <div className="text-xs text-ink-40 mt-1">отзывов оставлено</div>
            </div>
            <div className="flex-1 bg-surface rounded-card shadow-sm p-4 text-center">
              <div className="text-2xl font-extrabold text-ink-60 leading-none">
                {orders.length - reviewedCount}
              </div>
              <div className="text-xs text-ink-40 mt-1">ждут оценки</div>
            </div>
          </div>

          {/* Order list */}
          <section className="bg-surface rounded-card shadow-sm overflow-hidden">
            <div className="divide-y divide-line">
              {orders.map(order => {
                const combo = combos[order.combo_id ?? '']
                const comboImg = combo?.image || combo?.products?.[0]?.product_image
                const thumb = imgUrl(comboImg)
                const title = combo?.title || `Заказ #${order.id.slice(-6).toUpperCase()}`
                const shopName = combo?.shop_name
                const date = new Date(order.created_at).toLocaleDateString('ru-RU', {
                  day: 'numeric', month: 'long',
                })

                return (
                  <div key={order.id} className="px-4 py-4">
                    <div className="flex items-start gap-3">
                      {/* Thumbnail */}
                      <div className="w-12 h-12 rounded-[10px] bg-line/60 overflow-hidden flex-shrink-0 flex items-center justify-center mt-0.5">
                        {thumb ? (
                          <img src={thumb} alt={title} className="w-full h-full object-cover" />
                        ) : (
                          <Package className="h-5 w-5 text-ink-40" />
                        )}
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="text-sm font-semibold text-ink-100 truncate">{title}</div>
                            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                              <span className="text-xs text-ink-40">{date}</span>
                              {order.amount != null && (
                                <span className="text-xs font-semibold text-ink-60">{order.amount} ₽</span>
                              )}
                              {shopName && (
                                <span className="text-xs text-ink-40 truncate">{shopName}</span>
                              )}
                            </div>
                          </div>

                          {/* Action button */}
                          {!loadingReviews && (
                            reviews[order.id] === undefined ? null : (
                              reviews[order.id] === null ? (
                                <Link
                                  href={routes.reviewNew(order.id)}
                                  className="flex-shrink-0 flex items-center gap-1 text-xs font-semibold text-primary bg-primary-soft px-2.5 py-1.5 rounded-[8px] hover:bg-primary/20 transition-colors"
                                >
                                  <PenLine className="h-3 w-3" />
                                  Оценить
                                </Link>
                              ) : (
                                <Link
                                  href={routes.reviewNew(order.id)}
                                  className="flex-shrink-0 flex items-center gap-1 text-xs font-semibold text-ink-40 hover:text-ink-100 transition-colors"
                                >
                                  <ChevronRight className="h-3.5 w-3.5" />
                                </Link>
                              )
                            )
                          )}

                          {loadingReviews && (
                            <div className="w-16 h-6 bg-line/60 rounded animate-pulse flex-shrink-0" />
                          )}
                        </div>

                        {/* Review block */}
                        {!loadingReviews && reviews[order.id] && (
                          <div className="mt-2.5 p-3 bg-bg rounded-[10px] space-y-1">
                            <StarRow rating={reviews[order.id]!.rating} size={15} />
                            {reviews[order.id]!.comment && (
                              <p className="text-sm text-ink-60 leading-relaxed">
                                {reviews[order.id]!.comment}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
