'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { MapPin, Clock, Package, Star, CheckCircle2 } from 'lucide-react'
import { getOrder, getCombo, getReviewForOrder } from '@/lib/api'
import { routes } from '@/lib/routes'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/api\/?$/, '')

function buildImgUrl(path: string | null | undefined): string | null {
  if (!path) return null
  return path.startsWith('http') ? path : `${API_BASE}/uploads/${path.replace(/^\//, '')}`
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Ожидает оплаты', paid: 'Оплачено', completed: 'Получено',
  cancelled: 'Отменён', expired: 'Истёк срок',
}

const STATUS_PILL: Record<string, string> = {
  completed: 'bg-eco-soft text-eco',
  paid:      'bg-blue-50 text-blue-600',
  pending:   'bg-primary-soft text-warn',
  expired:   'bg-accent-soft text-accent',
  cancelled: 'bg-line text-ink-40',
}

function Stars({ rating }: { rating: number }) {
  return (
    <span className="inline-flex gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <svg key={i} width="14" height="14" viewBox="0 0 24 24"
          fill={i <= rating ? '#FFC629' : 'none'}
          stroke={i <= rating ? '#FFC629' : '#d1d5db'} strokeWidth="1.5">
          <path d="M12 2l3 7 7 1-5 5 1 7-6-4-6 4 1-7-5-5 7-1z" />
        </svg>
      ))}
    </span>
  )
}

function formatDt(dt: string | null | undefined) {
  if (!dt) return '—'
  const d = new Date(dt.endsWith('Z') ? dt : dt + 'Z')
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function HistoryDetailPage() {
  const { orderId } = useParams<{ orderId: string }>()
  const router = useRouter()
  const [order, setOrder] = useState<any>(null)
  const [combo, setCombo] = useState<any>(null)
  const [review, setReview] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getOrder(orderId)
      .then(async r => {
        const o = r.data
        setOrder(o)
        const promises: Promise<any>[] = []
        if (o?.combo_id) promises.push(getCombo(o.combo_id).then(cr => setCombo(cr.data)).catch(() => {}))
        if (o?.status === 'completed') promises.push(getReviewForOrder(orderId).then(rr => setReview(rr.data)).catch(() => {}))
        await Promise.all(promises)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [orderId])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )

  if (!order) return (
    <div className="px-4 py-10 text-center">
      <p className="text-ink-40">Заказ не найден</p>
      <Link href="/history" className="text-eco hover:underline mt-3 inline-block text-sm">← История покупок</Link>
    </div>
  )

  const comboImg = combo?.image || combo?.products?.[0]?.product_image
  const imgSrc = buildImgUrl(comboImg)

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 max-w-[540px] space-y-4">

      {/* Combo image + title */}
      {combo && (
        <div className="bg-surface rounded-card shadow-sm overflow-hidden">
          {imgSrc && (
            <div className="aspect-[16/7] overflow-hidden">
              <img src={imgSrc} alt={combo.title} className="w-full h-full object-cover" />
            </div>
          )}
          <div className="p-4">
            <p className="font-bold text-ink-100">{combo.title}</p>
            {combo.shop_name && <p className="text-sm text-ink-40 mt-0.5">{combo.shop_name}</p>}
          </div>
        </div>
      )}

      {/* Order info */}
      <div className="bg-surface rounded-card shadow-sm p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-ink-40">Статус</span>
          <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full ${STATUS_PILL[order.status] || 'bg-line text-ink-40'}`}>
            {STATUS_LABELS[order.status] || order.status}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-ink-40">Сумма</span>
          <span className="font-extrabold text-ink-100">{order.amount?.toLocaleString('ru-RU')} ₽</span>
        </div>
        {order.original_amount && order.original_amount !== order.amount && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-ink-40">Скидка</span>
            <span className="text-sm font-semibold text-eco">-{order.discount_rate}%</span>
          </div>
        )}
        <div className="border-t border-line pt-3 space-y-2.5">
          <div className="flex items-start gap-2">
            <Clock className="h-4 w-4 text-ink-40 mt-0.5 shrink-0" />
            <div>
              <p className="text-[11px] text-ink-40">Дата заказа</p>
              <p className="text-sm font-semibold text-ink-100">{formatDt(order.created_at)}</p>
            </div>
          </div>
          {order.paid_at && (
            <div className="flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-blue-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-[11px] text-ink-40">Оплачено</p>
                <p className="text-sm font-semibold text-ink-100">{formatDt(order.paid_at)}</p>
              </div>
            </div>
          )}
          {order.completed_at && (
            <div className="flex items-start gap-2">
              <Package className="h-4 w-4 text-eco mt-0.5 shrink-0" />
              <div>
                <p className="text-[11px] text-ink-40">Получено</p>
                <p className="text-sm font-semibold text-ink-100">{formatDt(order.completed_at)}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Locker info */}
      {combo?.locker_info && (
        <div className="bg-surface rounded-card shadow-sm p-4">
          <div className="flex items-start gap-3">
            <MapPin className="h-4 w-4 text-ink-40 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-sm text-ink-100">
                {combo.locker_info.locker_name || 'Постамат'}
                {combo.locker_info.unit_number ? ` · бокс №${combo.locker_info.unit_number}` : ''}
              </p>
              {combo.locker_info.locker_address && (
                <p className="text-xs text-ink-40 mt-0.5">{combo.locker_info.locker_address}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Access code */}
      {order.access_code && order.status === 'paid' && (
        <div className="bg-primary-soft border-2 border-primary rounded-card p-5 text-center">
          <p className="text-xs font-semibold text-ink-40 uppercase tracking-wider mb-2">Код для открытия ячейки</p>
          <p className="text-3xl font-extrabold text-ink-100 tracking-widest font-mono">{order.access_code}</p>
        </div>
      )}

      {/* Review */}
      {order.status === 'completed' && (
        review ? (
          <div className="bg-surface rounded-card shadow-sm p-4">
            <div className="flex items-center gap-2 mb-2">
              <Star className="h-4 w-4 text-primary fill-primary" />
              <span className="text-sm font-semibold text-ink-60">Ваш отзыв</span>
            </div>
            <Stars rating={review.rating} />
            {review.comment && <p className="text-sm text-ink-40 mt-2 leading-relaxed">{review.comment}</p>}
          </div>
        ) : (
          <Link
            href={routes.reviewNew(orderId)}
            className="block w-full bg-primary hover:bg-primary-hover text-ink-100 font-bold py-3.5 rounded-[10px] text-center transition-colors text-base"
          >
            Оставить отзыв
          </Link>
        )
      )}
    </div>
  )
}
