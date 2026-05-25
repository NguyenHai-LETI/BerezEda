'use client'

import { useState } from 'react'
import { Send, Mail, MessageCircle, Phone } from 'lucide-react'

const SUBJECTS = [
  'Проблема с заказом',
  'Вопрос по оплате',
  'Технические неполадки',
  'Предложение по улучшению',
  'Другое',
]

export default function ContactPage() {
  const [form, setForm] = useState({ subject: '', message: '' })
  const [sent, setSent] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  const inputCls = "w-full border border-line rounded-[10px] px-4 py-2.5 text-sm text-ink-100 bg-bg focus:outline-none focus:ring-2 focus:ring-primary/40"
  const labelCls = "text-xs font-semibold text-ink-40 block mb-1"

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.subject || !form.message.trim()) {
      setError('Пожалуйста, заполните все поля')
      return
    }
    setSending(true)
    setError('')
    await new Promise(r => setTimeout(r, 800))
    setSending(false)
    setSent(true)
  }

  if (sent) {
    return (
      <div className="px-4 md:px-6 lg:px-8 py-6 max-w-[540px] mx-auto w-full">
        <div className="bg-surface rounded-card shadow-sm p-10 flex flex-col items-center gap-4 text-center">
          <div className="w-14 h-14 rounded-full bg-eco-soft flex items-center justify-center">
            <Send className="h-7 w-7 text-eco" />
          </div>
          <h2 className="text-xl font-bold text-ink-100">Сообщение отправлено!</h2>
          <p className="text-sm text-ink-60">Мы ответим вам в течение 24 часов на ваш email.</p>
          <button
            onClick={() => { setSent(false); setForm({ subject: '', message: '' }) }}
            className="text-sm font-semibold text-primary hover:underline"
          >
            Отправить ещё
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-5 max-w-[540px] mx-auto w-full">
      <h2 className="text-xl font-bold text-ink-100">Связаться с нами</h2>

      {/* Contact channels */}
      <section className="bg-surface rounded-card shadow-sm overflow-hidden">
        <div className="divide-y divide-line">
          {[
            { icon: Mail, label: 'Email', value: 'support@foodbox.ru', href: 'mailto:support@foodbox.ru' },
            { icon: MessageCircle, label: 'Telegram', value: '@foodbox_support', href: 'https://t.me/foodbox_support' },
            { icon: Phone, label: 'Телефон', value: '+7 800 123 45 67', href: 'tel:+78001234567' },
          ].map(({ icon: Icon, label, value, href }) => (
            <a key={label} href={href} className="flex items-center gap-4 px-5 py-3.5 hover:bg-bg/60 transition-colors">
              <div className="w-8 h-8 rounded-[8px] bg-line/60 flex items-center justify-center shrink-0">
                <Icon className="h-4 w-4 text-ink-60" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs text-ink-40">{label}</div>
                <div className="text-sm font-semibold text-ink-100">{value}</div>
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* Contact form */}
      <section className="bg-surface rounded-card shadow-sm p-5">
        <h3 className="text-base font-bold text-ink-100 mb-4">Написать нам</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={labelCls}>Тема обращения</label>
            <select
              value={form.subject}
              onChange={e => setForm(f => ({ ...f, subject: e.target.value }))}
              className={inputCls}
            >
              <option value="">Выберите тему</option>
              {SUBJECTS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className={labelCls}>Сообщение</label>
            <textarea
              value={form.message}
              onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
              placeholder="Опишите вашу проблему или вопрос..."
              rows={5}
              className={inputCls + ' resize-none'}
            />
          </div>
          {error && <p className="text-xs text-accent">{error}</p>}
          <button
            type="submit"
            disabled={sending}
            className="w-full bg-primary hover:bg-primary-hover disabled:opacity-50 text-ink-100 font-bold py-3 rounded-[10px] text-sm transition-colors flex items-center justify-center gap-2"
          >
            <Send className="h-4 w-4" />
            {sending ? 'Отправка...' : 'Отправить сообщение'}
          </button>
        </form>
      </section>

      <p className="text-xs text-ink-40 text-center">Время ответа: обычно до 24 часов в рабочие дни</p>
    </div>
  )
}
