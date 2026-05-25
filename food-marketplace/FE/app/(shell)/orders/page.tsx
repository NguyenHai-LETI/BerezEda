'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getOrders } from '@/lib/api'
import { ORDER_STATUS_LABELS } from '@/lib/constants'

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  paid: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-gray-100 text-gray-500',
  expired: 'bg-red-100 text-red-600',
}

export default function OrdersPage() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getOrders(year, month).then(r => setOrders(r.data || [])).finally(() => setLoading(false))
  }, [year, month])

  function prevMonth() {
    if (month === 1) { setMonth(12); setYear(y => y-1) }
    else setMonth(m => m-1)
  }
  function nextMonth() {
    const today = new Date()
    if (year === today.getFullYear() && month === today.getMonth()+1) return
    if (month === 12) { setMonth(1); setYear(y => y+1) }
    else setMonth(m => m+1)
  }

  const MONTHS_RU = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']

  return (
    <div className="max-w-lg mx-auto px-4 py-6">
      <h1 className="text-xl font-bold text-gray-900 mb-4">История покупок</h1>

      {/* Month selector */}
      <div className="flex items-center justify-between bg-white rounded-2xl border border-gray-100 px-4 py-3 mb-6">
        <button onClick={prevMonth} className="text-gray-400 hover:text-gray-700 text-xl font-bold w-8">‹</button>
        <span className="font-semibold text-gray-900">{MONTHS_RU[month-1]} {year}</span>
        <button onClick={nextMonth} className="text-gray-400 hover:text-gray-700 text-xl font-bold w-8">›</button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1,2,3].map(i => <div key={i} className="h-20 bg-gray-100 rounded-2xl animate-pulse"/>)}
        </div>
      ) : orders.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-4xl mb-2">🧾</p>
          <p>Нет покупок за этот период</p>
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map(order => (
            <Link key={order.id} href={`/orders/${order.id}`}>
              <div className="bg-white rounded-2xl border border-gray-100 p-4 hover:shadow-md transition">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-gray-400">
                      {new Date(order.created_at).toLocaleDateString('ru-RU', {day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'})}
                    </p>
                    <p className="font-semibold text-gray-900 mt-1">{order.amount.toLocaleString('ru-RU')} ₽</p>
                    <p className="text-xs text-gray-400 mt-0.5">Код доступа: {order.access_code}</p>
                  </div>
                  <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${STATUS_COLORS[order.status] || 'bg-gray-100'}`}>
                    {ORDER_STATUS_LABELS[order.status] || order.status}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
