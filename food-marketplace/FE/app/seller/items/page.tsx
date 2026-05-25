'use client'
import { useEffect, useRef, useState } from 'react'
import { getMyCombos, cancelCombo, confirmComboPlaced } from '@/lib/api'
import Link from 'next/link'
import Image from 'next/image'
import { Package, MapPin } from 'lucide-react'
import ConfirmModal from '@/components/ConfirmModal'
import { CountdownBadge } from '@/components/CountdownBadge'

function getImageUrl(img: string) {
  if (!img) return ''
  if (img.startsWith('http') || img.startsWith('blob:')) return ''
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api'
  const origin = apiUrl.replace(/\/api\/?$/, '')
  return `${origin}/uploads/${img}`
}

function normalizeStatus(status: string) {
  return status?.toLowerCase() ?? ''
}

const STATUS_LABEL: Record<string, string> = {
  draft: 'Черновик', available: 'В продаже', ready: 'Ожидает размещения',
  sold: 'Продан', expired: 'Истёк', cancelled: 'Отменён',
}
const STATUS_COLOR: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600', available: 'bg-green-100 text-green-700',
  ready: 'bg-yellow-100 text-yellow-700', sold: 'bg-blue-100 text-blue-700',
  expired: 'bg-orange-100 text-orange-700', cancelled: 'bg-red-100 text-red-700',
}

const TABS = ['all', 'draft', 'available', 'sold', 'expired', 'cancelled']
const TAB_LABEL: Record<string, string> = {
  all: 'Все', draft: 'Черновик', available: 'В продаже',
  sold: 'Продан', expired: 'Истёк', cancelled: 'Отменён',
}

export default function SellerItemsPage() {
  const [combos, setCombos] = useState<any[]>([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [actionId, setActionId] = useState<string | null>(null)
  const [confirmAction, setConfirmAction] = useState<{ type: 'cancel' | 'publish'; id: string } | null>(null)
  const [tick, setTick] = useState(0)
  const expiredReadyIdsRef = useRef<Set<string>>(new Set())

  const load = () => {
    setLoading(true)
    getMyCombos().then(data => {
      setCombos(data.data || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  // Tick every second when there are ready combos — forces re-render so countdown is computed fresh
  useEffect(() => {
    const hasReady = combos.some(c => normalizeStatus(c.status) === 'ready' && c.ready_deadline)
    if (!hasReady) return
    const id = setInterval(() => setTick(t => t + 1), 1000)
    return () => clearInterval(id)
  }, [combos])

  const filtered = filter === 'all'
    ? combos
    : combos.filter(c => normalizeStatus(c.status) === filter)

  const handleConfirmAction = async () => {
    if (!confirmAction) return
    const { type, id } = confirmAction
    setConfirmAction(null)
    setActionId(id)
    try {
      if (type === 'cancel') await cancelCombo(id)
      else await confirmComboPlaced(id)
      load()
    } finally { setActionId(null) }
  }

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Мои наборы</h1>
        <Link href="/seller/add-item"
          className="bg-yellow-400 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-yellow-500">
          + Добавить
        </Link>
      </div>
      <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
        {TABS.map(s => (
          <button key={s} onClick={() => setFilter(s)}
            className={"px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors " +
              (filter === s ? 'bg-yellow-400 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200')}>
            {TAB_LABEL[s]}
          </button>
        ))}
      </div>
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-400"/>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <Package className="h-10 w-10 text-gray-300 mx-auto mb-2" aria-hidden="true" />
          <p>Наборов нет</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((combo: any) => {
            const status = normalizeStatus(combo.status)
            const comboImg = combo.image ? getImageUrl(combo.image) : ''
            const firstProductImage = combo.products?.find((p: any) => p.product_image)?.product_image
            const thumbUrl = comboImg || (firstProductImage ? getImageUrl(firstProductImage) : '')
            const lockerInfo = combo.locker_info

            const endTime = combo.sale_end_time
              ? (combo.sale_end_time.endsWith('Z') ? combo.sale_end_time : combo.sale_end_time + 'Z')
              : null
            const secsLeft = endTime
              ? Math.max(0, Math.floor((new Date(endTime).getTime() - Date.now()) / 1000))
              : 0

            const readyDeadlineMs = status === 'ready' && combo.ready_deadline
              ? new Date(combo.ready_deadline.endsWith('Z') ? combo.ready_deadline : combo.ready_deadline + 'Z').getTime()
              : null
            const readySecsLeft = readyDeadlineMs !== null
              ? Math.max(0, Math.floor((readyDeadlineMs - Date.now()) / 1000))
              : null
            const readyIsExpired = readySecsLeft === 0
            const readyIsUrgent = readySecsLeft !== null && readySecsLeft > 0 && readySecsLeft < 120

            // Trigger reload once when this combo's countdown hits 0
            if (readyIsExpired && readyDeadlineMs !== null && !expiredReadyIdsRef.current.has(combo.id)) {
              expiredReadyIdsRef.current.add(combo.id)
              setTimeout(() => load(), 2000)
            }

            const cardContent = (
              <>
                <div className="flex gap-3 mb-2">
                  <div className="w-16 h-16 rounded-lg overflow-hidden bg-gray-100 shrink-0 relative">
                    {thumbUrl ? (
                      <Image src={thumbUrl} alt={combo.title} fill className="object-cover" unoptimized />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center"><Package className="h-6 w-6 text-gray-300" aria-hidden="true" /></div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start">
                      <div className="font-medium text-gray-800 truncate">{combo.title}</div>
                      <div className="flex items-center gap-1.5 ml-2 shrink-0">
                        {status === 'available' && secsLeft > 0 && (
                          <CountdownBadge seconds={secsLeft} className="bg-orange-100 text-orange-700 text-xs" />
                        )}
                        {status === 'ready' && readySecsLeft !== null && (
                          <span className={"text-xs px-2 py-1 rounded-full font-mono font-semibold whitespace-nowrap " +
                            (readyIsExpired ? 'bg-gray-100 text-gray-400' : readyIsUrgent ? 'bg-red-100 text-red-600' : 'bg-yellow-50 text-yellow-700')}>
                            {readyIsExpired ? 'Отменяется...' : `⏱ ${String(Math.floor(readySecsLeft / 60)).padStart(2, '0')}:${String(readySecsLeft % 60).padStart(2, '0')}`}
                          </span>
                        )}
                        <span className={"text-xs px-2 py-1 rounded-full whitespace-nowrap " +
                          (readyIsExpired ? 'bg-gray-100 text-gray-400' : STATUS_COLOR[status] || 'bg-gray-100 text-gray-600')}>
                          {readyIsExpired ? 'Отменяется...' : STATUS_LABEL[status] || combo.status}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-sm font-semibold text-yellow-600">{combo.sale_price} ₽</span>
                      {combo.original_price && combo.original_price > combo.sale_price && (
                        <span className="text-xs text-gray-400 line-through">{combo.original_price} ₽</span>
                      )}
                      {combo.discount_rate > 0 && (
                        <span className="text-xs text-gray-500">· {combo.discount_rate}% скидка</span>
                      )}
                    </div>
                    {lockerInfo && (
                      <div className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                        <MapPin className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
                        <span>{lockerInfo.locker_name}</span>
                        {lockerInfo.unit_number != null && (
                          <span className="bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded font-medium">#{lockerInfo.unit_number}</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {endTime && !(status === 'available' && secsLeft > 0) && (
                  <div className="text-xs text-gray-400 mb-3">
                    <span>До: {new Date(endTime).toLocaleString('ru', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                )}

                <div className="flex gap-2">
                  {status === 'draft' && (
                    <button onClick={(e) => { e.preventDefault(); setConfirmAction({ type: 'publish', id: combo.id }) }} disabled={actionId === combo.id}
                      className="text-xs bg-yellow-400 text-white px-3 py-1.5 rounded-lg hover:bg-yellow-500 disabled:opacity-50">
                      Опубликовать
                    </button>
                  )}
                  {status === 'available' && (
                    <button onClick={(e) => { e.preventDefault(); setConfirmAction({ type: 'cancel', id: combo.id }) }} disabled={actionId === combo.id}
                      className="text-xs bg-red-50 text-red-600 px-3 py-1.5 rounded-lg hover:bg-red-100 disabled:opacity-50">
                      Снять с продажи
                    </button>
                  )}
                  {status === 'ready' && !readyIsExpired && (
                    <span className={"text-xs px-3 py-1.5 rounded-lg font-medium " + (readyIsUrgent ? 'bg-red-50 text-red-600' : 'bg-yellow-50 text-yellow-700')}>
                      Перейти к размещению →
                    </span>
                  )}
                </div>
              </>
            )

            if (status === 'ready' && !readyIsExpired) {
              return (
                <Link key={combo.id} href={`/seller/items/${combo.id}`}
                  className={"block bg-white rounded-xl p-4 shadow-sm border transition-colors " +
                    (readyIsUrgent ? 'border-red-200 hover:border-red-300' : 'border-yellow-200 hover:border-yellow-300')}>
                  {cardContent}
                </Link>
              )
            }

            return (
              <div key={combo.id}
                className={"bg-white rounded-xl p-4 shadow-sm border border-gray-100 " + (readyIsExpired ? 'opacity-50' : '')}>
                {cardContent}
              </div>
            )
          })}
        </div>
      )}

      <ConfirmModal
        open={!!confirmAction}
        title={confirmAction?.type === 'cancel' ? 'Снять с продажи?' : 'Опубликовать набор?'}
        message={confirmAction?.type === 'cancel'
          ? 'Набор будет снят с продажи и станет недоступен покупателями.'
          : 'Набор будет выставлен на продажу.'}
        confirmText={confirmAction?.type === 'cancel' ? 'Да, снять' : 'Да, опубликовать'}
        onConfirm={handleConfirmAction}
        onCancel={() => setConfirmAction(null)}
      />
    </div>
  )
}
