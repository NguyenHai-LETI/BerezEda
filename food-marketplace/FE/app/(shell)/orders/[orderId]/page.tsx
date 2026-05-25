'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { AlertTriangle, Package } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { getOrder, pickupOrder } from '@/lib/api'
import ConfirmModal from '@/components/ConfirmModal'

/** Parse naive-UTC string from API as UTC, display in local timezone */
function formatDate(raw?: string) {
  if (!raw) return ''
  const d = new Date(raw.endsWith('Z') ? raw : raw + 'Z')
  return d.toLocaleString('ru-RU')
}

interface Order {
  id: string
  status: string
  amount: number
  discount_rate?: number
  access_code?: string
  pickup_code?: string
  pickup_deadline?: string
  created_at: string
  paid_at?: string
  completed_at?: string
  combo?: {
    name: string
  }
}

const STATUS_LABELS: Record<string, string> = {
  'READY_FOR_PICKUP': 'Ожидает получения',
  'paid': 'Оплачен',
  'completed': 'Получен',
  'COMPLETED': 'Получен',
  'cancelled': 'Отменён',
  'CANCELLED': 'Отменён',
}

export default function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>()
  const router = useRouter()
  const [order, setOrder] = useState<Order | null>(null)
  const [loading, setLoading] = useState(true)
  const [picking, setPicking] = useState(false)
  const [error, setError] = useState('')
  const [showPickupConfirm, setShowPickupConfirm] = useState(false)
  const [countdown, setCountdown] = useState<number | null>(null)

  useEffect(() => {
    getOrder(orderId)
      .then(r => setOrder(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [orderId])

  // Calculate pickup deadline countdown
  useEffect(() => {
    if (!order?.pickup_deadline) return

    const calculateCountdown = () => {
      const raw = order.pickup_deadline!
      const deadline = new Date(raw.endsWith('Z') ? raw : raw + 'Z').getTime()
      const now = Date.now()
      const remaining = Math.max(0, deadline - now)
      const minutes = Math.floor(remaining / 60000)
      setCountdown(minutes)
    }

    calculateCountdown()
    const timer = setInterval(calculateCountdown, 60000) // Update every minute
    return () => clearInterval(timer)
  }, [order?.pickup_deadline])

  async function handlePickupDirect() {
    if (!order?.access_code) return
    setShowPickupConfirm(false)
    setPicking(true)
    setError('')
    try {
      const res = await pickupOrder(orderId, order.access_code)
      setOrder(res.data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setPicking(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-400" />
    </div>
  )

  if (!order) return (
    <div className="p-4 text-center text-gray-500">
      Заказ не найден
    </div>
  )

  const rawCode = order.access_code || order.pickup_code || ''
  const accessCode = /^(AA|BB)\d{6}$/.test(rawCode) ? rawCode.slice(2) : rawCode
  const isReadyForPickup = ['READY_FOR_PICKUP', 'paid'].includes(order.status)
  const isCompleted = ['completed', 'COMPLETED'].includes(order.status)

  return (
    <div className="max-w-lg mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Детали заказа</h1>

      {/* Access code block — shown for orders ready for pickup */}
      {isReadyForPickup && accessCode && (
        <div className="bg-yellow-50 border-2 border-yellow-400 rounded-2xl p-6 mb-6 text-center">
          <p className="text-sm text-gray-600 mb-1">🔑 Код получения</p>
          <p className="text-4xl font-bold text-yellow-600 tracking-widest font-mono my-2">
            {accessCode}
          </p>
          {/* QR code for locker simulator scanning */}
          <div className="flex justify-center my-3">
            <QRCodeSVG value={String(rawCode)} size={140} />
          </div>
          <p className="text-xs text-gray-400 mb-2">Quét mã QR trên Locker Simulator để lấy hàng</p>
          {countdown !== null && countdown > 0 && (
            <p className="text-xs text-red-600 font-semibold">
              ⏱ Осталось {countdown} мин. для получения
            </p>
          )}
          {countdown === 0 && (
            <p className="text-xs text-red-600 font-semibold">
              <AlertTriangle className="h-4 w-4 inline mr-1" aria-hidden="true" /> Срок получения истёк
            </p>
          )}
        </div>
      )}

      {/* Order Info */}
      <div className="bg-white rounded-2xl border border-gray-100 divide-y divide-gray-50 mb-6">
        <div className="px-4 py-3 text-sm">
          <span className="text-gray-500">Статус</span>
          <span className="float-right font-medium text-gray-900">
            {STATUS_LABELS[order.status] || order.status}
          </span>
        </div>
        {order.combo?.name && (
          <div className="px-4 py-3 text-sm">
            <span className="text-gray-500">Товар</span>
            <span className="float-right font-medium text-gray-900">{order.combo.name}</span>
          </div>
        )}
        <div className="px-4 py-3 text-sm">
          <span className="text-gray-500">Сумма</span>
          <span className="float-right font-medium text-gray-900">
            {order.amount?.toLocaleString('ru-RU') || '0'} ₽
          </span>
        </div>
        {order.discount_rate && order.discount_rate > 0 && (
          <div className="px-4 py-3 text-sm">
            <span className="text-gray-500">Скидка</span>
            <span className="float-right font-medium text-green-600">-{order.discount_rate}%</span>
          </div>
        )}
        <div className="px-4 py-3 text-sm">
          <span className="text-gray-500">Дата заказа</span>
          <span className="float-right font-medium text-gray-900">
            {formatDate(order.created_at)}
          </span>
        </div>
        {order.paid_at && (
          <div className="px-4 py-3 text-sm">
            <span className="text-gray-500">Дата оплаты</span>
            <span className="float-right font-medium text-gray-900">
              {formatDate(order.paid_at)}
            </span>
          </div>
        )}
        {order.completed_at && (
          <div className="px-4 py-3 text-sm">
            <span className="text-gray-500">Дата получения</span>
            <span className="float-right font-medium text-gray-900">
              {formatDate(order.completed_at)}
            </span>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl p-3 mb-6 text-center">
          {error}
        </div>
      )}

      {/* Actions for orders ready for pickup */}
      {isReadyForPickup && (
        <div className="space-y-3">
          {/* Primary: go to locker sim */}
          <Link
            href={`/locker-sim?code=${accessCode}`}
            className="block w-full bg-yellow-400 hover:bg-yellow-500 text-black font-bold py-4 rounded-2xl text-center text-lg transition"
          >
            <Package className="h-4 w-4 inline mr-1" aria-hidden="true" /> Забрать из постамата
          </Link>

          {/* Secondary: direct confirm without sim */}
          <button
            onClick={() => setShowPickupConfirm(true)}
            disabled={picking}
            className="w-full border-2 border-gray-200 text-gray-600 font-medium py-3 rounded-2xl transition hover:bg-gray-50 disabled:opacity-50 text-sm"
          >
            {picking ? 'Обработка...' : 'Подтвердить получение'}
          </button>
        </div>
      )}

      {/* Review button for completed orders */}
      {isCompleted && (
        <button
          onClick={() => router.push(`/reviews/new?order_id=${order.id}`)}
          className="w-full border-2 border-yellow-400 text-yellow-600 font-bold py-4 rounded-2xl mt-4 transition hover:bg-yellow-50 text-lg"
        >
          ★ Написать отзыв
        </button>
      )}

      {/* Back Button */}
      <div className="mt-4 text-center">
        <button
          onClick={() => router.back()}
          className="text-sm text-gray-400 hover:text-gray-600"
        >
          &larr; Назад
        </button>
      </div>

      <ConfirmModal
        open={showPickupConfirm}
        title="Подтвердить получение?"
        message="Вы подтверждаете, что забрали заказ из постамата."
        confirmText="Да, подтвердить"
        onConfirm={handlePickupDirect}
        onCancel={() => setShowPickupConfirm(false)}
      />
    </div>
  )
}
