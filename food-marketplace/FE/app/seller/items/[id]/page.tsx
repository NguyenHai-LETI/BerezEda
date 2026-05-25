'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { getCombo, cancelCombo, confirmComboPlaced } from '@/lib/api'
import { QRCodeSVG } from 'qrcode.react'
import ConfirmModal from '@/components/ConfirmModal'

const STATUS_LABEL: Record<string, string> = {
  draft: 'Черновик', ready: 'Готов к размещению', available: 'В продаже', sold: 'Продан',
  expired: 'Истёк', cancelled: 'Отменён',
}

function useCountdown(isoDeadline: string | null | undefined) {
  const [secsLeft, setSecsLeft] = useState<number | null>(null)
  useEffect(() => {
    if (!isoDeadline) { setSecsLeft(null); return }
    const deadline = new Date(isoDeadline.endsWith('Z') ? isoDeadline : isoDeadline + 'Z').getTime()
    const tick = () => setSecsLeft(Math.max(0, Math.floor((deadline - Date.now()) / 1000)))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [isoDeadline])
  return secsLeft
}

export default function SellerItemDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [combo, setCombo] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState('')
  const [confirmAction, setConfirmAction] = useState<'cancel' | 'publish' | null>(null)

  const readySecsLeft = useCountdown(combo?.status === 'ready' ? combo?.ready_deadline : null)

  useEffect(() => {
    getCombo(id)
      .then(r => setCombo(r.data))
      .catch(() => setCombo(null))
      .finally(() => setLoading(false))
  }, [id])

  async function handleConfirmAction() {
    const action = confirmAction
    setConfirmAction(null)
    if (!action) return
    setActionLoading(true)
    setError('')
    try {
      const r = action === 'cancel' ? await cancelCombo(id) : await confirmComboPlaced(id)
      setCombo(r.data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-400"/>
    </div>
  )
  if (!combo) return (
    <div className="p-4 text-center text-gray-500">
      <p>Набор не найден</p>
      <button onClick={() => router.back()} className="mt-4 text-yellow-500 underline text-sm">Назад</button>
    </div>
  )

  const saleTimeLeft = combo.sale_end_time
    ? Math.max(0, Math.floor((new Date(combo.sale_end_time.endsWith('Z') ? combo.sale_end_time : combo.sale_end_time + 'Z').getTime() - Date.now()) / 60000))
    : null

  // ── Ready state: show full placement UI (step 4 equivalent) ─────────────────
  if (combo.status === 'ready') {
    const mins = readySecsLeft !== null ? Math.floor(readySecsLeft / 60) : null
    const secs = readySecsLeft !== null ? readySecsLeft % 60 : null
    const isUrgent = readySecsLeft !== null && readySecsLeft < 120

    return (
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px 32px 48px' }}>
        <button
          onClick={() => router.push('/seller/items')}
          className="flex items-center gap-1.5 mb-6 font-semibold"
          style={{ fontSize: 13, color: '#8a8a8a' }}
        >
          ← Мои наборы
        </button>

        <div className="grid gap-6" style={{ gridTemplateColumns: '1fr 1fr', alignItems: 'start' }}>
          {/* Left: code + QR */}
          <div>
            <div className="mb-5">
              <h2 className="font-extrabold m-0 mb-1" style={{ fontSize: 24, letterSpacing: '-0.02em' }}>Код доступа</h2>
              <p style={{ fontSize: 14, color: '#8a8a8a', margin: 0 }}>Покупатель использует этот код для получения товара.</p>
            </div>

            <div style={{ background: '#fff', border: '1px solid #e1e0db', borderRadius: 14, padding: '18px 18px 14px' }}>
              <p className="font-bold uppercase" style={{ fontSize: 10.5, letterSpacing: '0.12em', color: '#8a8a8a', marginBottom: 12 }}>
                Код для покупателя
              </p>
              <div className="font-mono font-extrabold text-center" style={{ fontSize: 40, letterSpacing: '0.15em', color: '#1a1a1a', marginBottom: 20 }}>
                {combo.access_code}
              </div>
              <div className="flex justify-center" style={{ marginBottom: 8 }}>
                <QRCodeSVG value={String(combo.access_code)} size={160} />
              </div>
            </div>
          </div>

          {/* Right: summary + countdown + instructions */}
          <div className="flex flex-col gap-4">
            <div style={{ background: '#fff', border: '1px solid #e1e0db', borderRadius: 14, padding: '14px 16px' }}>
              <p className="font-bold uppercase" style={{ fontSize: 10.5, letterSpacing: '0.12em', color: '#8a8a8a', marginBottom: 8 }}>
                Набор
              </p>
              {[
                { label: 'Название', val: combo.title },
                { label: 'Цена', val: `${combo.sale_price} ₽` },
                { label: 'Статус', val: <span style={{ color: '#C88A1B', fontWeight: 700 }}>Готов к размещению</span> },
              ].map((row, i) => (
                <div key={i} className="flex justify-between py-2" style={{ fontSize: 13, borderTop: '1px solid #ececea' }}>
                  <span style={{ color: '#8a8a8a' }}>{row.label}</span>
                  <b>{row.val}</b>
                </div>
              ))}
              {combo.locker_info?.locker_name && (
                <div className="flex justify-between py-2" style={{ fontSize: 13, borderTop: '1px solid #ececea' }}>
                  <span style={{ color: '#8a8a8a' }}>Постамат</span>
                  <b>{combo.locker_info.locker_name} #{combo.locker_info.unit_number}</b>
                </div>
              )}
            </div>

            {readySecsLeft !== null && (
              <div style={{ padding: '12px 16px', borderRadius: 12, background: isUrgent ? '#FFEDE7' : '#f7f6f3', border: `1px solid ${isUrgent ? '#f3cec3' : '#e1e0db'}` }}>
                <p className="font-bold" style={{ fontSize: 12, color: isUrgent ? '#E8553D' : '#4a4a4a', marginBottom: 4 }}>
                  Время на размещение
                </p>
                <p className="font-extrabold font-mono" style={{ fontSize: 28, letterSpacing: '0.05em', color: isUrgent ? '#E8553D' : '#1a1a1a', margin: 0 }}>
                  {String(mins).padStart(2, '0')}:{String(secs).padStart(2, '0')}
                </p>
                <p style={{ fontSize: 11.5, color: '#8a8a8a', marginTop: 4 }}>
                  Если не разместить вовремя, набор будет отменён
                </p>
              </div>
            )}

            <div style={{ padding: '14px 16px', borderRadius: 12, background: '#FFF8E1', border: '1px solid #f5d97a' }}>
              <p className="font-bold" style={{ fontSize: 13, color: '#8a6d00', marginBottom: 8 }}>Инструкция по размещению:</p>
              <ol className="list-decimal list-inside flex flex-col gap-1" style={{ fontSize: 12.5, color: '#4a4a4a' }}>
                <li>Откройте ячейку с помощью приложения</li>
                <li>Поместите продукты в ячейку</li>
                <li>Закройте ячейку</li>
                <li>Нажмите кнопку ниже для начала продажи</li>
              </ol>
            </div>
          </div>
        </div>

        {error && <p style={{ color: '#E8553D', fontSize: 13, textAlign: 'center', marginTop: 16 }}>{error}</p>}

        <div className="flex flex-col gap-3 mt-6">
          <button
            onClick={() => setConfirmAction('publish')}
            disabled={actionLoading}
            className="w-full flex items-center justify-center gap-2 font-bold transition-all disabled:opacity-50"
            style={{ padding: '16px 22px', borderRadius: 12, fontSize: 15, background: '#2E7D5B', color: 'white' }}
          >
            {actionLoading ? 'Подтверждение...' : 'Я положил товар в ячейку → Начать продажу'}
          </button>
          <button
            onClick={() => setConfirmAction('cancel')}
            disabled={actionLoading}
            className="w-full font-semibold transition-all disabled:opacity-50"
            style={{ padding: '12px 22px', borderRadius: 12, fontSize: 14, border: '1px solid #e1e0db', background: '#fff', color: '#8a8a8a' }}
          >
            Отменить набор
          </button>
        </div>

        <ConfirmModal
          open={!!confirmAction}
          title={confirmAction === 'cancel' ? 'Отменить набор?' : 'Начать продажу?'}
          message={confirmAction === 'cancel'
            ? 'Набор будет отменён, ячейка освободится.'
            : 'Набор будет выставлен на продажу. Убедитесь, что товар размещён в ячейке.'}
          confirmText={confirmAction === 'cancel' ? 'Да, отменить' : 'Да, начать продажу'}
          onConfirm={handleConfirmAction}
          onCancel={() => setConfirmAction(null)}
        />
      </div>
    )
  }

  // ── Other statuses: standard detail view ────────────────────────────────────
  return (
    <div className="max-w-lg mx-auto px-4 py-6">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => router.back()} className="text-gray-400 hover:text-gray-700">←</button>
        <h1 className="text-xl font-bold text-gray-900">Детали набора</h1>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-4">
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 flex-1 mr-2">{combo.title}</h2>
          <span className={`text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap ${
            combo.status === 'available' ? 'bg-green-100 text-green-700' :
            combo.status === 'sold' ? 'bg-blue-100 text-blue-700' :
            combo.status === 'draft' ? 'bg-gray-100 text-gray-600' :
            'bg-orange-100 text-orange-700'
          }`}>
            {STATUS_LABEL[combo.status] || combo.status}
          </span>
        </div>

        {combo.description && (
          <p className="text-sm text-gray-500 mb-4">{combo.description}</p>
        )}

        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-gray-50 rounded-xl p-3">
            <p className="text-xs text-gray-500">Цена до скидки</p>
            <p className="font-semibold text-gray-700">{combo.original_price?.toLocaleString('ru-RU')} ₽</p>
          </div>
          <div className="bg-yellow-50 rounded-xl p-3">
            <p className="text-xs text-gray-500">Цена продажи (-{combo.discount_rate}%)</p>
            <p className="font-bold text-yellow-600">{combo.sale_price?.toLocaleString('ru-RU')} ₽</p>
          </div>
        </div>

        {combo.sale_end_time && (
          <div className="bg-gray-50 rounded-xl p-3 mb-4">
            <p className="text-xs text-gray-500 mb-1">Время продажи</p>
            <p className="text-sm text-gray-700">
              до {new Date(combo.sale_end_time.endsWith('Z') ? combo.sale_end_time : combo.sale_end_time + 'Z').toLocaleString('ru-RU')}
            </p>
            {saleTimeLeft !== null && saleTimeLeft > 0 && (
              <p className="text-xs text-orange-600 mt-1">Осталось: {saleTimeLeft} мин</p>
            )}
          </div>
        )}

        {combo.status === 'available' && combo.access_code && (
          <div className="bg-blue-50 rounded-xl p-3 mb-4">
            <p className="text-xs text-blue-600 mb-1">Код доступа к ячейке</p>
            <p className="text-2xl font-bold text-blue-800 tracking-widest">
              {/^(AA|BB)\d{6}$/.test(combo.access_code) ? combo.access_code.slice(2) : combo.access_code}
            </p>
          </div>
        )}

        {combo.products && combo.products.length > 0 && (
          <div>
            <p className="text-xs text-gray-500 mb-2">Состав набора:</p>
            <div className="space-y-1">
              {combo.products.map((p: any) => (
                <div key={p.id} className="flex justify-between text-sm">
                  <span className="text-gray-700">{p.product_name || p.product_id}</span>
                  <span className="text-gray-500">× {p.quantity}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {error && <p className="text-red-500 text-sm text-center mb-4">{error}</p>}

      <div className="space-y-3">
        {combo.status === 'draft' && (
          <button
            onClick={() => router.push('/seller/add-item')}
            className="w-full bg-yellow-400 hover:bg-yellow-500 text-black font-bold py-4 rounded-2xl text-lg transition"
          >
            Выбрать постамат и опубликовать →
          </button>
        )}
        {combo.status === 'available' && (
          <button
            onClick={() => setConfirmAction('cancel')}
            disabled={actionLoading}
            className="w-full border-2 border-red-200 text-red-600 font-medium py-3 rounded-2xl transition hover:bg-red-50 disabled:opacity-50"
          >
            {actionLoading ? 'Отмена...' : 'Снять с продажи'}
          </button>
        )}
        <button
          onClick={() => router.push('/seller/items')}
          className="w-full border-2 border-gray-200 text-gray-600 font-medium py-3 rounded-2xl transition hover:bg-gray-50"
        >
          ← Назад к списку
        </button>
      </div>

      <ConfirmModal
        open={!!confirmAction}
        title={confirmAction === 'cancel' ? 'Снять с продажи?' : 'Начать продажу?'}
        message={confirmAction === 'cancel'
          ? 'Набор будет снят с продажи и станет недоступен покупателям.'
          : 'Набор будет выставлен на продажу. Убедитесь, что товар размещён в ячейке.'}
        confirmText={confirmAction === 'cancel' ? 'Да, снять' : 'Да, начать продажу'}
        onConfirm={handleConfirmAction}
        onCancel={() => setConfirmAction(null)}
      />
    </div>
  )
}
