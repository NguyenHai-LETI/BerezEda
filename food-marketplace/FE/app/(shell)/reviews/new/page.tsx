'use client'
import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import { getOrder, getCombo, createReview } from '@/lib/api'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
const API_BASE = API_URL.replace(/\/api\/?$/, '')

function buildImgUrl(path: string | null | undefined): string | null {
  if (!path) return null
  return path.startsWith('http') ? path : `${API_BASE}/uploads/${path.replace(/^\//, '')}`
}

const RATING_LABELS = ['', 'Плохо', 'Так себе', 'Нормально', 'Хорошо', 'Отлично']

function StarDisplay({ rating }: { rating: number }) {
  return (
    <div className="flex gap-1.5">
      {[1, 2, 3, 4, 5].map(i => (
        <svg key={i} width="32" height="32" viewBox="0 0 24 24"
          fill={i <= rating ? '#FFC629' : 'none'}
          stroke={i <= rating ? '#FFC629' : '#d1d5db'}
          strokeWidth="1.5">
          <path d="M12 2l3 7 7 1-5 5 1 7-6-4-6 4 1-7-5-5 7-1z" />
        </svg>
      ))}
    </div>
  )
}

function StarInput({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [hover, setHover] = useState(0)
  return (
    <div className="flex gap-2">
      {[1, 2, 3, 4, 5].map(i => (
        <button
          key={i}
          type="button"
          onMouseEnter={() => setHover(i)}
          onMouseLeave={() => setHover(0)}
          onClick={() => onChange(i)}
          aria-label={`${i} звезда`}
        >
          <svg width="40" height="40" viewBox="0 0 24 24"
            fill={i <= (hover || value) ? '#FFC629' : 'none'}
            stroke={i <= (hover || value) ? '#FFC629' : '#d1d5db'}
            strokeWidth="1.5"
            className="transition">
            <path d="M12 2l3 7 7 1-5 5 1 7-6-4-6 4 1-7-5-5 7-1z" />
          </svg>
        </button>
      ))}
    </div>
  )
}

function ReviewForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const orderId = searchParams.get('order_id')

  const [combo, setCombo] = useState<any>(null)
  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [existingReview, setExistingReview] = useState<{ rating: number; comment?: string } | null>(null)

  useEffect(() => {
    if (!orderId) { setLoading(false); return }

    Promise.all([
      // Load order + combo info
      getOrder(orderId)
        .then(r => {
          const o = r.data
          if (o?.combo_id) return getCombo(o.combo_id).then(cr => setCombo(cr.data))
        })
        .catch(() => {}),

      // Check if review already exists — use raw fetch with fresh token (after
      // getOrder() above has handled any needed token refresh via request())
      (async () => {
        try {
          const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
          const r = await fetch(`${API_URL}/reviews/order/${orderId}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          })
          if (!r.ok) return
          const json = await r.json()
          const d = json?.data
          if (d && typeof d === 'object' && typeof d.rating === 'number') {
            setExistingReview({ rating: d.rating, comment: d.comment ?? undefined })
          }
        } catch {}
      })(),
    ]).finally(() => setLoading(false))
  }, [orderId])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (rating === 0) { setError('Выберите оценку'); return }
    if (!orderId) { setError('Заказ не найден'); return }
    setSubmitting(true)
    setError('')
    try {
      await createReview({ order_id: orderId, rating, comment: comment.trim() || undefined })
      router.replace('/mypage/reviews')
    } catch (err: any) {
      // Review already exists → treat as success and go back
      if (err.message?.includes('уже оставлен')) {
        router.replace('/mypage/reviews')
        return
      }
      setError(err.message || 'Ошибка при сохранении отзыва')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-400" />
    </div>
  )

  const comboImg = combo?.image || combo?.products?.[0]?.product_image
  const imgSrc = buildImgUrl(comboImg)

  return (
    <div className="max-w-lg mx-auto px-4 py-6">

      {/* Combo preview */}
      {combo && (
        <div className="flex items-center gap-3 bg-white border border-gray-100 rounded-2xl p-4 mb-6">
          <div className="w-14 h-14 rounded-xl bg-stone-100 overflow-hidden flex-shrink-0">
            {imgSrc && <img src={imgSrc} alt={combo.title} className="w-full h-full object-cover" />}
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-gray-900 text-sm truncate">{combo.title}</p>
            {combo.shop_name && <p className="text-xs text-gray-400 mt-0.5">{combo.shop_name}</p>}
          </div>
        </div>
      )}

      {existingReview ? (
        /* Read-only view of existing review */
        <div className="space-y-4">
          <div className="bg-white border border-gray-100 rounded-2xl p-5 space-y-3">
            <p className="text-sm font-semibold text-gray-500">Ваш отзыв</p>
            <StarDisplay rating={existingReview.rating} />
            <p className="text-sm font-semibold text-yellow-600">{RATING_LABELS[existingReview.rating]}</p>
            {existingReview.comment && (
              <p className="text-sm text-gray-700 leading-relaxed border-t border-gray-100 pt-3">
                {existingReview.comment}
              </p>
            )}
          </div>
          <p className="text-center text-sm text-gray-400">Отзыв уже был оставлен</p>
          <button
            onClick={() => router.replace('/mypage/reviews')}
            className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold py-3.5 rounded-2xl transition text-base"
          >
            Назад к отзывам
          </button>
        </div>
      ) : (
        /* New review form */
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Star rating */}
          <div className="bg-white border border-gray-100 rounded-2xl p-5">
            <p className="text-sm font-semibold text-gray-700 mb-3">Ваша оценка</p>
            <StarInput value={rating} onChange={setRating} />
            {rating > 0 && (
              <p className="text-sm font-semibold text-yellow-600 mt-2">{RATING_LABELS[rating]}</p>
            )}
          </div>

          {/* Comment */}
          <div className="bg-white border border-gray-100 rounded-2xl p-5">
            <p className="text-sm font-semibold text-gray-700 mb-3">
              Комментарий <span className="text-gray-400 font-normal">(необязательно)</span>
            </p>
            <textarea
              value={comment}
              onChange={e => setComment(e.target.value)}
              placeholder="Расскажите о качестве продуктов, упаковке, удобстве получения..."
              rows={4}
              maxLength={2000}
              className="w-full resize-none border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 text-gray-900 placeholder-gray-400"
            />
            <p className="text-xs text-gray-400 text-right mt-1">{comment.length}/2000</p>
          </div>

          {error && <p className="text-red-500 text-sm text-center">{error}</p>}

          <button
            type="submit"
            disabled={submitting || rating === 0}
            className="w-full bg-[#FFC629] hover:bg-yellow-400 disabled:opacity-40 disabled:cursor-not-allowed text-gray-900 font-bold py-3.5 rounded-2xl transition text-base"
          >
            {submitting ? 'Сохранение...' : 'Отправить отзыв'}
          </button>
        </form>
      )}
    </div>
  )
}

export default function NewReviewPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-400" /></div>}>
      <ReviewForm />
    </Suspense>
  )
}
