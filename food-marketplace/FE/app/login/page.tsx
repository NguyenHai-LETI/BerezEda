'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { login } from '@/lib/api'
import { saveAuth } from '@/lib/auth'
import { APP_NAME } from '@/lib/constants'
import { Mail, Lock, ArrowRight } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await login(email, password)
      saveAuth(res.data.access, res.data.refresh, res.data.user)
      const role = res.data.user.role
      if (role === 'owner_shop') router.replace('/seller')
      else if (role === 'owner_locker') router.replace('/locker-owner')
      else if (role === 'admin') router.replace('/admin')
      else router.replace('/')
    } catch (err: any) {
      setError(err.message || 'Ошибка входа')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid min-h-screen" style={{ gridTemplateColumns: '1.1fr 1fr' }}>
      {/* ── Left panel ── */}
      <div
        className="relative flex flex-col overflow-hidden px-12 py-9"
        style={{
          background: '#1a1a1a',
          color: '#f3f1ec',
        }}
      >
        {/* ambient gradients */}
        <div className="pointer-events-none absolute inset-0"
          style={{
            background: 'radial-gradient(80% 60% at 20% 30%, rgba(255,198,41,.12), transparent 60%), radial-gradient(60% 40% at 80% 80%, rgba(46,125,91,.12), transparent 60%)',
          }}
        />

        {/* Brand */}
        <div className="relative z-10 flex items-center gap-3">
          <div
            className="grid place-items-center rounded-xl font-extrabold text-base flex-shrink-0"
            style={{ width: 36, height: 36, background: '#FFC629', color: '#1a1a1a' }}
          >
            Б
          </div>
          <div>
            <div className="font-extrabold text-white" style={{ fontSize: 16, letterSpacing: '-0.01em' }}>
              {APP_NAME}
            </div>
          </div>
        </div>

        {/* Hero */}
        <div className="relative z-10 my-auto max-w-lg">
          <p
            className="font-mono mb-4"
            style={{ fontSize: 12, color: '#FFC629', letterSpacing: '0.12em' }}
          >
            /// LESS WASTE. MORE TASTE.
          </p>
          <h1
            className="font-extrabold text-white m-0"
            style={{ fontSize: 44, letterSpacing: '-0.025em', lineHeight: 1.12 }}
          >
            Одна платформа — для всех, кто спасает еду.
          </h1>
          <p style={{ fontSize: 16, color: '#b0b0b0', lineHeight: 1.55, margin: '24px 0 32px', maxWidth: 480 }}>
            Покупатели, рестораны и партнёры в одном кабинете. Выберите вашу роль при входе — мы откроем нужный раздел.
          </p>

          {/* Stats */}
          <div
            className="flex items-stretch gap-6"
            style={{
              padding: '20px 22px',
              background: 'rgba(255,255,255,.04)',
              border: '1px solid rgba(255,255,255,.08)',
              borderRadius: 14,
              backdropFilter: 'blur(8px)',
            }}
          >
            <div className="flex-1">
              <div className="font-extrabold text-white" style={{ fontSize: 26, letterSpacing: '-0.02em' }}>12&nbsp;800</div>
              <div style={{ fontSize: 12, color: '#a0a0a0', marginTop: 4, lineHeight: 1.3 }}>кг еды спасено сетью</div>
            </div>
            <div style={{ width: 1, background: 'rgba(255,255,255,.1)' }} />
            <div className="flex-1">
              <div className="font-extrabold text-white" style={{ fontSize: 26, letterSpacing: '-0.02em' }}>340</div>
              <div style={{ fontSize: 12, color: '#a0a0a0', marginTop: 4, lineHeight: 1.3 }}>партнёрских ресторанов</div>
            </div>
            <div style={{ width: 1, background: 'rgba(255,255,255,.1)' }} />
            <div className="flex-1">
              <div className="font-extrabold text-white" style={{ fontSize: 26, letterSpacing: '-0.02em' }}>−45%</div>
              <div style={{ fontSize: 12, color: '#a0a0a0', marginTop: 4, lineHeight: 1.3 }}>средняя цена для покупателя</div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div
          className="relative z-10 flex items-center gap-4 pt-6"
          style={{ fontSize: 12.5, color: '#808080', borderTop: '1px solid rgba(255,255,255,.08)' }}
        >
          <span>© 2026 {APP_NAME}</span>
          <span>Поддержка</span>
          <span>Документация API</span>
        </div>
      </div>

      {/* ── Right panel ── */}
      <div className="grid place-items-center bg-bg p-10">
        <div
          className="w-full"
          style={{
            maxWidth: 420,
            background: '#fff',
            border: '1px solid #e1e0db',
            borderRadius: 18,
            padding: 36,
            boxShadow: '0 8px 24px rgba(20,20,20,.08), 0 0 0 1px rgba(20,20,20,.04)',
          }}
        >
          <h2
            className="font-extrabold m-0 mb-1"
            style={{ fontSize: 22, letterSpacing: '-0.02em' }}
          >
            Вход в ЛК
          </h2>
          <p className="text-ink-40 mt-0 mb-7" style={{ fontSize: 13.5 }}>
            Войдите, чтобы продолжить
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <label className="block">
              <span className="block font-semibold mb-1.5" style={{ fontSize: 13, color: '#1a1a1a' }}>
                Email
              </span>
              <div
                className="flex items-center gap-2.5 px-3 transition-colors"
                style={{
                  background: '#f7f6f3',
                  border: '1.5px solid transparent',
                  borderRadius: 11,
                }}
                onFocus={(e) => {
                  const wrap = e.currentTarget
                  wrap.style.background = '#fff'
                  wrap.style.borderColor = '#1a1a1a'
                }}
                onBlur={(e) => {
                  if (!e.currentTarget.contains(e.relatedTarget)) {
                    const wrap = e.currentTarget
                    wrap.style.background = '#f7f6f3'
                    wrap.style.borderColor = 'transparent'
                  }
                }}
              >
                <Mail className="flex-shrink-0 text-ink-40" size={15} strokeWidth={1.8} />
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  placeholder="manager@example.com"
                  className="flex-1 bg-transparent border-none outline-none py-3 text-ink-100"
                  style={{ fontSize: 14.5 }}
                />
              </div>
            </label>

            {/* Password */}
            <label className="block">
              <span className="flex justify-between items-center font-semibold mb-1.5" style={{ fontSize: 13, color: '#1a1a1a' }}>
                Пароль
                <span className="font-medium text-ink-40" style={{ fontSize: 12 }}>Забыли пароль?</span>
              </span>
              <div
                className="flex items-center gap-2.5 px-3 transition-colors"
                style={{
                  background: '#f7f6f3',
                  border: '1.5px solid transparent',
                  borderRadius: 11,
                }}
                onFocus={(e) => {
                  const wrap = e.currentTarget
                  wrap.style.background = '#fff'
                  wrap.style.borderColor = '#1a1a1a'
                }}
                onBlur={(e) => {
                  if (!e.currentTarget.contains(e.relatedTarget)) {
                    const wrap = e.currentTarget
                    wrap.style.background = '#f7f6f3'
                    wrap.style.borderColor = 'transparent'
                  }
                }}
              >
                <Lock className="flex-shrink-0 text-ink-40" size={15} strokeWidth={1.8} />
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="flex-1 bg-transparent border-none outline-none py-3 text-ink-100"
                  style={{ fontSize: 14.5 }}
                />
                <button
                  type="button"
                  onClick={() => setShowPass(v => !v)}
                  className="font-semibold text-ink-40 hover:text-ink-100 transition-colors px-2 py-1 rounded"
                  style={{ fontSize: 12 }}
                >
                  {showPass ? 'Скрыть' : 'Показать'}
                </button>
              </div>
            </label>

            {/* Remember */}
            <label className="flex items-center gap-2 cursor-pointer" style={{ fontSize: 13, color: '#4a4a4a' }}>
              <input type="checkbox" defaultChecked className="w-4 h-4 rounded accent-ink-100" />
              <span>Запомнить меня на 30 дней</span>
            </label>

            {error && (
              <p className="text-accent text-sm text-center">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 font-bold transition-all disabled:opacity-50"
              style={{
                background: '#FFC629',
                color: '#1a1a1a',
                borderRadius: 12,
                padding: '13px 22px',
                fontSize: 14.5,
              }}
              onMouseEnter={e => { if (!loading) (e.currentTarget.style.boxShadow = '0 6px 18px rgba(255,198,41,.4)') }}
              onMouseLeave={e => { (e.currentTarget.style.boxShadow = 'none') }}
            >
              {loading ? 'Вход...' : 'Войти'}
              {!loading && <ArrowRight size={16} strokeWidth={2.2} />}
            </button>
          </form>

          <p className="text-center mt-5 text-ink-40" style={{ fontSize: 13 }}>
            Новый в {APP_NAME}?{' '}
            <Link href="/register" className="text-ink-100 font-bold hover:text-accent transition-colors">
              Создать аккаунт
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
