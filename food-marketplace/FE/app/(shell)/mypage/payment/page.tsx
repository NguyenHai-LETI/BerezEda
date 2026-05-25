'use client'

import { useEffect, useState } from 'react'
import { CreditCard, Plus, Trash2, CheckCircle2 } from 'lucide-react'
import { getCards, addCard, deleteCard, setDefaultCard } from '@/lib/api'

interface Card {
  id: string
  card_number_masked?: string
  brand?: string
  expire?: string
  holder_name?: string
  is_default?: boolean
}

export default function PaymentPage() {
  const [cards, setCards] = useState<Card[]>([])
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState('')

  async function load() {
    try {
      const res: any = await getCards()
      setCards(res.data || [])
    } catch {
      setCards([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleAdd() {
    setAdding(true)
    setError('')
    try {
      const res: any = await addCard()
      if (res?.data?.link_url) {
        window.open(res.data.link_url, '_blank')
        setTimeout(load, 3000)
      }
    } catch (e: any) {
      setError(e.message || 'Ошибка добавления карты')
    } finally {
      setAdding(false)
    }
  }

  async function handleDelete(cardId: string) {
    setDeletingId(cardId)
    try {
      await deleteCard(cardId)
      setCards(prev => prev.filter(c => c.id !== cardId))
    } catch (e: any) {
      setError(e.message || 'Ошибка удаления')
    } finally {
      setDeletingId(null)
    }
  }

  async function handleSetDefault(cardId: string) {
    try {
      await setDefaultCard(cardId)
      setCards(prev => prev.map(c => ({ ...c, is_default: c.id === cardId })))
    } catch (e: any) {
      setError(e.message || 'Ошибка')
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-5 max-w-[540px] mx-auto w-full">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-ink-100">Способы оплаты</h2>
        <button
          onClick={handleAdd}
          disabled={adding}
          className="flex items-center gap-1.5 text-sm font-semibold text-primary disabled:opacity-50"
        >
          <Plus className="h-4 w-4" />
          {adding ? 'Добавление...' : 'Добавить карту'}
        </button>
      </div>

      {error && <p className="text-sm text-accent text-center">{error}</p>}

      {cards.length === 0 ? (
        <section className="bg-surface rounded-card shadow-sm p-10 flex flex-col items-center gap-4 text-center">
          <div className="w-14 h-14 rounded-full bg-line/60 flex items-center justify-center">
            <CreditCard className="h-7 w-7 text-ink-40" />
          </div>
          <div>
            <p className="font-semibold text-ink-60 mb-1">Нет добавленных карт</p>
            <p className="text-sm text-ink-40">Добавьте карту для быстрой оплаты заказов</p>
          </div>
          <button
            onClick={handleAdd}
            disabled={adding}
            className="bg-primary hover:bg-primary-hover disabled:opacity-50 text-ink-100 font-bold py-2.5 px-6 rounded-[10px] text-sm transition-colors"
          >
            {adding ? 'Добавление...' : '+ Добавить карту'}
          </button>
        </section>
      ) : (
        <section className="bg-surface rounded-card shadow-sm overflow-hidden">
          <div className="divide-y divide-line">
            {cards.map(card => (
              <div key={card.id} className="flex items-center gap-4 px-5 py-4">
                <div className="w-10 h-10 rounded-[10px] bg-line/60 flex items-center justify-center shrink-0">
                  <CreditCard className="h-5 w-5 text-ink-60" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-ink-100">
                      {card.brand || 'Карта'} •••• {card.card_number_masked?.slice(-4) || '****'}
                    </span>
                    {card.is_default && (
                      <CheckCircle2 className="h-4 w-4 text-eco shrink-0" />
                    )}
                  </div>
                  {card.expire && (
                    <div className="text-xs text-ink-40 mt-0.5">Действует до {card.expire}</div>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {!card.is_default && (
                    <button
                      onClick={() => handleSetDefault(card.id)}
                      className="text-xs font-semibold text-primary hover:text-primary/80"
                    >
                      По умолчанию
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(card.id)}
                    disabled={deletingId === card.id}
                    className="w-8 h-8 flex items-center justify-center rounded-[8px] text-ink-40 hover:bg-accent/10 hover:text-accent transition-colors disabled:opacity-50"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <p className="text-xs text-ink-40 text-center px-4">
        Платёжные данные надёжно защищены. Мы не храним данные карт на своих серверах.
      </p>
    </div>
  )
}
