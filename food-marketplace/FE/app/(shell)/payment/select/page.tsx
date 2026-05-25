'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { QRCodeSVG } from 'qrcode.react'
import { AlertTriangle, MapPin, Clock } from 'lucide-react'
import {
  registerFincodeCustomer,
  getCards,
  addCard,
  deleteCard,
  setDefaultCard,
  createOrder,
  executePayment,
  getOrder,
  pickupOrder,
  getCombo,
  getLocker,
} from '@/lib/api'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/api\/?$/, '')

function buildImgUrl(path: string | null | undefined): string | null {
  if (!path) return null
  return path.startsWith('http') ? path : `${API_BASE}/uploads/${path.replace(/^\//, '')}`
}

interface Card {
  id: string
  card_id: string
  fincode_card_id: string
  card_number_masked: string
  card_no: string
  brand: string
  expire: string
  holder_name: string
  is_default: boolean
}

const CARD_LIMIT = 4

export default function PaymentSelectPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const comboId = searchParams.get('combo_id')

  const [combo, setCombo] = useState<any>(null)
  const [locker, setLocker] = useState<any>(null)
  const [cards, setCards] = useState<Card[]>([])
  const [selectedCardId, setSelectedCardId] = useState<string>('')
  const [confirmed, setConfirmed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [paying, setPaying] = useState(false)
  const [error, setError] = useState('')
  const [successData, setSuccessData] = useState<{ orderId: string; accessCode: string } | null>(null)
  const [orderDetail, setOrderDetail] = useState<any>(null)
  const [simulating, setSimulating] = useState(false)
  const [simDone, setSimDone] = useState(false)

  const loadCards = useCallback(async () => {
    const res = await getCards()
    const raw: any[] = res.data || []
    const list: Card[] = raw.map(c => ({
      ...c,
      id: c.id || c.card_id || '',
      card_number_masked: c.card_number_masked || c.card_no || '****',
    }))
    setCards(list)
    const def = list.find(c => c.is_default)
    setSelectedCardId(prev => prev || def?.id || list[0]?.id || '')
    return list
  }, [])

  useEffect(() => {
    if (!comboId) { setLoading(false); return }
    async function init() {
      try {
        const comboRes = await getCombo(comboId)
        const comboData = comboRes.data
        setCombo(comboData)
        if (comboData.locker_location_id) {
          try {
            const lockerRes = await getLocker(comboData.locker_location_id)
            setLocker(lockerRes.data)
          } catch {}
        }
      } catch {}
      const isRegistered = typeof window !== 'undefined' && localStorage.getItem('fincode_registered') === 'true'
      if (!isRegistered) {
        try {
          await registerFincodeCustomer()
          localStorage.setItem('fincode_registered', 'true')
        } catch {}
      }
      try {
        await loadCards()
      } catch {
        setError('Не удалось загрузить список карт')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [comboId, loadCards])

  useEffect(() => {
    function onMessage(e: MessageEvent) {
      if (e.origin !== window.location.origin) return
      if (e.data?.type === 'CARD_REGISTERED') loadCards()
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [loadCards])

  async function handleAddCard() {
    setError('')
    try {
      const res = await addCard(comboId ?? undefined)
      const url: string = res?.data?.card_registration_url
      if (!url) { setError('Не удалось получить URL от Fincode'); return }
      const popup = window.open(url, '_blank')
      if (!popup) window.location.href = url
    } catch (err: any) {
      setError(err.message || 'Не удалось создать сессию регистрации карты')
    }
  }

  async function handleRefreshCards() {
    setError('')
    try { await loadCards() }
    catch { setError('Не удалось обновить список карт') }
  }

  async function handleDeleteCard(cardId: string) {
    setError('')
    try {
      await deleteCard(cardId)
      const remaining = cards.filter(c => c.id !== cardId)
      setCards(remaining)
      if (selectedCardId === cardId) setSelectedCardId(remaining[0]?.id || '')
    } catch (err: any) {
      setError(err.message || 'Не удалось удалить карту')
    }
  }

  async function handleSetDefault(cardId: string) {
    setError('')
    try {
      await setDefaultCard(cardId)
      setCards(prev => prev.map(c => ({ ...c, is_default: c.id === cardId })))
    } catch (err: any) {
      setError(err.message || 'Не удалось установить карту по умолчанию')
    }
  }

  async function handleBuy() {
    if (!selectedCardId || !comboId || !confirmed) return
    setPaying(true)
    setError('')
    try {
      const orderRes = await createOrder(comboId)
      const order = orderRes.data
      if (!order?.id) throw new Error('Не удалось создать заказ')
      await executePayment(order.id, selectedCardId)
      // Fetch updated order to get the BB access_code set by mark_order_paid()
      let finalAccessCode = order.access_code || ''
      try {
        const detail = await getOrder(order.id)
        const updated = detail?.data || detail
        setOrderDetail(updated)
        if (updated?.access_code) finalAccessCode = updated.access_code
      } catch {}
      setSuccessData({ orderId: order.id, accessCode: finalAccessCode })
    } catch (err: any) {
      setError(err.message || 'Ошибка при обработке платежа')
      setPaying(false)
    }
  }

  // Loading
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (!comboId) {
    return <div className="max-w-lg mx-auto px-4 py-10 text-center text-ink-40">Набор не найден</div>
  }

  // Success screen
  if (successData) {
    async function handleSimulate() {
      if (!successData) return
      setSimulating(true)
      try { await pickupOrder(successData.orderId, successData.accessCode) } catch {}
      setSimDone(true)
      setSimulating(false)
    }

    const salePrice = combo?.sale_price || combo?.selling_price || 0
    const originalPrice = combo?.original_price || 0

    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-120px)] px-4 py-8">
        <div className="bg-surface rounded-card shadow-md w-full max-w-sm p-7 text-center">
          <div className="text-4xl mb-4">🎉</div>
          <h2 className="text-xl font-extrabold text-ink-100 mb-2">Оплата завершена!</h2>
          <p className="text-sm text-ink-40 mb-5">Используйте код получения, чтобы забрать товар из локера</p>

          {/* QR block */}
          <div className="bg-primary-soft border-2 border-primary rounded-[14px] p-5 mb-5">
            <p className="text-xs font-semibold text-ink-40 uppercase tracking-wider mb-2">Код получения</p>
            <p className="text-4xl font-extrabold text-ink-100 font-mono tracking-wider mb-4">
              {/^(AA|BB)\d{6}$/.test(successData.accessCode) ? successData.accessCode.slice(2) : successData.accessCode}
            </p>
            <div className="flex justify-center mb-3">
              <QRCodeSVG value={String(successData.accessCode)} size={140} />
            </div>
            <div className="flex items-center justify-center gap-1.5 text-xs font-semibold text-accent">
              <Clock className="h-3.5 w-3.5" />
              <span>Заберите в течение <b>30 минут</b>!</span>
            </div>
          </div>

          {/* Price summary */}
          {(orderDetail?.amount != null || salePrice > 0) && (
            <div className="bg-bg rounded-[10px] p-4 text-left text-sm space-y-1.5 mb-5">
              <div className="flex justify-between">
                <span className="text-ink-40">Сумма оплаты</span>
                <span className="font-bold text-ink-100">{(orderDetail?.amount ?? salePrice).toLocaleString('ru-RU')} ₽</span>
              </div>
              {orderDetail?.original_amount != null && orderDetail.original_amount !== orderDetail.amount && (
                <div className="flex justify-between">
                  <span className="text-ink-40">Скидка</span>
                  <span className="text-eco font-semibold">−{(orderDetail.original_amount - orderDetail.amount).toLocaleString('ru-RU')} ₽</span>
                </div>
              )}
              {!orderDetail && originalPrice > salePrice && (
                <div className="flex justify-between">
                  <span className="text-ink-40">Скидка</span>
                  <span className="text-eco font-semibold">−{(originalPrice - salePrice).toLocaleString('ru-RU')} ₽</span>
                </div>
              )}
            </div>
          )}

          {simDone ? (
            <button
              onClick={() => router.push('/history')}
              className="w-full bg-primary hover:bg-primary-hover text-ink-100 font-bold py-3 rounded-[10px] transition-colors"
            >
              История заказов
            </button>
          ) : (
            <button
              onClick={handleSimulate}
              disabled={simulating}
              className="w-full bg-line text-ink-60 hover:bg-line2 disabled:opacity-50 font-bold py-3 rounded-[10px] transition-colors"
            >
              {simulating ? 'Обработка...' : 'Симулировать получение товара'}
            </button>
          )}
          <button onClick={() => router.push('/')} className="w-full mt-3 text-sm font-semibold text-ink-40 hover:text-ink-60 transition-colors">
            На главную →
          </button>
        </div>
      </div>
    )
  }

  // Main checkout screen
  const salePrice = combo?.sale_price || combo?.selling_price || 0
  const originalPrice = combo?.original_price || 0
  const discount = originalPrice > salePrice ? originalPrice - salePrice : 0

  return (
    <div className="flex justify-center px-4 py-6">
      <div className="w-full max-w-lg space-y-4">

        {/* Order summary card */}
        {combo && (
          <div className="bg-surface rounded-card shadow-sm p-5 space-y-4">
            {/* Product row */}
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-[10px] bg-line/60 shrink-0 overflow-hidden">
                {(() => {
                  const imgSrc = buildImgUrl(combo.image || combo.products?.[0]?.product_image)
                  return imgSrc ? (
                    <img src={imgSrc} alt={combo.title || combo.name || ''} className="w-full h-full object-cover" />
                  ) : null
                })()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-bold text-ink-100 truncate">{combo.title || combo.name}</div>
                {combo.shop_name && <div className="text-xs text-ink-40 truncate">{combo.shop_name}</div>}
              </div>
              <div className="text-right shrink-0">
                <div className="text-base font-extrabold text-ink-100">{salePrice.toLocaleString('ru-RU')} ₽</div>
                {originalPrice > salePrice && (
                  <div className="text-xs text-ink-40 line-through">{originalPrice.toLocaleString('ru-RU')} ₽</div>
                )}
              </div>
            </div>

            {/* Location */}
            {locker && (
              <div className="flex items-start gap-3 bg-bg rounded-[10px] px-4 py-3">
                <MapPin className="h-4 w-4 text-ink-40 mt-0.5 shrink-0" />
                <div>
                  <div className="text-xs font-semibold text-ink-60">Место получения</div>
                  <div className="text-sm font-bold text-ink-100 leading-tight">{locker.name}</div>
                  <div className="text-xs text-ink-40">{locker.address}</div>
                </div>
              </div>
            )}

            {/* Warning */}
            <div className="flex items-start gap-3 bg-warn-soft rounded-[10px] px-4 py-3">
              <AlertTriangle className="h-4 w-4 text-warn mt-0.5 shrink-0" />
              <p className="text-xs text-warn">
                <b>Важно:</b> заберите товар в течение <b>30 минут</b> после оплаты, иначе заказ будет отменён.
              </p>
            </div>

            {/* Price summary */}
            <div className="border-t border-line pt-4 space-y-2">
              {originalPrice > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-ink-40">Цена набора</span>
                  <span className="font-semibold text-ink-100">{originalPrice.toLocaleString('ru-RU')} ₽</span>
                </div>
              )}
              {discount > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-ink-40">Скидка</span>
                  <span className="font-semibold text-eco">−{discount.toLocaleString('ru-RU')} ₽</span>
                </div>
              )}
              <div className="flex justify-between text-base pt-1 border-t border-line">
                <span className="font-bold text-ink-100">К оплате</span>
                <span className="font-extrabold text-ink-100">{salePrice.toLocaleString('ru-RU')} ₽</span>
              </div>
            </div>
          </div>
        )}

        {/* Payment method */}
        <div className="bg-surface rounded-card shadow-sm p-5 space-y-3">
          <div className="text-sm font-bold text-ink-100 mb-1">Способ оплаты</div>

          {cards.length === 0 ? (
            <div className="bg-primary-soft rounded-[10px] p-5 text-center">
              <p className="text-sm text-ink-60 mb-4">Нет сохранённых карт</p>
              <button
                onClick={handleAddCard}
                className="w-full bg-primary hover:bg-primary-hover text-ink-100 font-bold py-3 rounded-[10px] text-sm transition-colors"
              >
                Добавить карту
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {cards.map(card => (
                <div
                  key={card.id}
                  onClick={() => setSelectedCardId(card.id)}
                  className={`rounded-[10px] border-2 p-4 cursor-pointer transition-colors ${
                    selectedCardId === card.id ? 'border-primary bg-primary-soft' : 'border-line bg-bg hover:border-line2'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {/* Radio */}
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors ${
                      selectedCardId === card.id ? 'border-primary-hover bg-primary-hover' : 'border-line2'
                    }`}>
                      {selectedCardId === card.id && <div className="w-2 h-2 bg-white rounded-full" />}
                    </div>
                    {/* Card info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[11px] font-bold bg-ink-100 text-white px-1.5 py-0.5 rounded">{card.brand || 'CARD'}</span>
                        <span className="text-sm font-bold text-ink-100 font-mono">{card.card_number_masked}</span>
                        {card.is_default && (
                          <span className="text-[11px] bg-eco-soft text-eco font-semibold px-2 py-0.5 rounded-full">Основная</span>
                        )}
                      </div>
                      {card.holder_name && <p className="text-xs text-ink-40 mt-0.5">{card.holder_name}</p>}
                      <p className="text-xs text-ink-40">Срок: {card.expire}</p>
                    </div>
                  </div>
                  {selectedCardId === card.id && (
                    <div className="mt-3 pt-3 border-t border-primary/20 flex items-center gap-4" onClick={e => e.stopPropagation()}>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={card.is_default}
                          onChange={() => { if (!card.is_default) handleSetDefault(card.id) }}
                          disabled={card.is_default}
                          className="w-3.5 h-3.5 accent-primary"
                        />
                        <span className="text-xs text-ink-60">{card.is_default ? 'Основная карта' : 'Сделать основной'}</span>
                      </label>
                      <button
                        onClick={() => handleDeleteCard(card.id)}
                        className="text-xs text-accent hover:underline"
                      >
                        Удалить
                      </button>
                    </div>
                  )}
                </div>
              ))}

              {cards.length < CARD_LIMIT && (
                <button
                  onClick={handleAddCard}
                  className="w-full border-2 border-dashed border-line2 hover:border-primary text-ink-40 hover:text-ink-60 font-semibold py-3 rounded-[10px] text-sm transition-colors"
                >
                  + Добавить карту (макс. {CARD_LIMIT})
                </button>
              )}

              <button onClick={handleRefreshCards} className="w-full text-xs text-ink-40 hover:text-ink-60 py-1 transition-colors">
                ↻ Обновить список карт
              </button>
            </div>
          )}
        </div>

        {/* Confirm + pay */}
        <div className="bg-surface rounded-card shadow-sm p-5 space-y-4">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={e => setConfirmed(e.target.checked)}
              className="w-4 h-4 mt-0.5 accent-primary shrink-0"
            />
            <span className="text-sm text-ink-60">Я ознакомился с условиями и подтверждаю покупку.</span>
          </label>

          {error && (
            <div className="bg-accent-soft border border-accent/20 text-accent text-sm rounded-[10px] px-4 py-3 text-center">
              {error}
            </div>
          )}

          {cards.length > 0 && (
            <button
              onClick={handleBuy}
              disabled={!selectedCardId || paying || !confirmed}
              className="w-full bg-primary hover:bg-primary-hover disabled:opacity-40 text-ink-100 font-extrabold py-4 rounded-[10px] text-base transition-colors"
            >
              {paying ? 'Обработка...' : `Оплатить ${salePrice.toLocaleString('ru-RU')} ₽`}
            </button>
          )}

          <button onClick={() => router.back()} className="w-full text-sm font-semibold text-ink-40 hover:text-ink-60 transition-colors py-1">
            ← Назад
          </button>
        </div>
      </div>
    </div>
  )
}
