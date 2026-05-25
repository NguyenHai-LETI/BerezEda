'use client'
import { useEffect, useState } from 'react'
import {
  adminCreateUser, getUsersByRole, syncLockersToFirebase,
  getOrders, getCombos, getLockers, getSalesSummary, getShops,
} from '@/lib/api'
import { Users, ShoppingBag, Package, Lock, TrendingUp, RefreshCw } from 'lucide-react'

type UserItem = {
  id: string; email: string; name?: string; role: string; is_active: boolean; created_at: string
}

const USER_TABS = [
  { key: 'owner_shop', label: 'Владельцы магазинов' },
  { key: 'owner_locker', label: 'Владельцы локеров' },
] as const

const NAV_TABS = [
  { key: 'users', label: 'Пользователи', icon: Users },
  { key: 'orders', label: 'Заказы', icon: ShoppingBag },
  { key: 'combos', label: 'Наборы', icon: Package },
  { key: 'lockers', label: 'Постаматы', icon: Lock },
  { key: 'analytics', label: 'Аналитика', icon: TrendingUp },
] as const

type NavTab = (typeof NAV_TABS)[number]['key']

// ── Users section ──────────────────────────────────────────────────────────────
function UsersSection() {
  const [userTab, setUserTab] = useState<'owner_shop' | 'owner_locker'>('owner_shop')
  const [users, setUsers] = useState<UserItem[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ email: '', password: '', name: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [syncing, setSyncing] = useState(false)

  const loadUsers = async (role: string) => {
    setLoading(true)
    try { const res = await getUsersByRole(role); setUsers(res.data || []) }
    catch { setUsers([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { loadUsers(userTab) }, [userTab])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true); setError(''); setSuccess('')
    try {
      await adminCreateUser(form.email, form.password, form.name, userTab)
      setSuccess('Аккаунт создан')
      setForm({ email: '', password: '', name: '' })
      setShowForm(false)
      loadUsers(userTab)
    } catch (err: any) { setError(err.message || 'Ошибка создания') }
    finally { setSaving(false) }
  }

  const handleSync = async () => {
    setSyncing(true)
    try { const res = await syncLockersToFirebase(); setSuccess(res.message || 'Синхронизация завершена') }
    catch (err: any) { setError(err.message || 'Ошибка') }
    finally { setSyncing(false) }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold text-gray-900">Управление пользователями</h2>
        <button onClick={handleSync} disabled={syncing}
          className="flex items-center gap-1.5 bg-blue-500 hover:bg-blue-600 text-white text-sm font-semibold px-3 py-2 rounded-xl transition disabled:opacity-50">
          <RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />
          Sync Firebase
        </button>
      </div>

      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-4">
        {USER_TABS.map(t => (
          <button key={t.key} onClick={() => { setUserTab(t.key); setShowForm(false); setError(''); setSuccess('') }}
            className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition ${userTab === t.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex justify-between items-center mb-3">
        <p className="text-sm text-gray-500">{loading ? 'Загрузка...' : `${users.length} пользователей`}</p>
        <button onClick={() => { setShowForm(!showForm); setError(''); setSuccess('') }}
          className="bg-yellow-400 hover:bg-yellow-500 text-black text-sm font-semibold px-4 py-2 rounded-xl transition">
          {showForm ? 'Отмена' : `+ Создать ${userTab === 'owner_shop' ? 'владельца магазина' : 'владельца локера'}`}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-xl border border-gray-200 p-5 mb-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { field: 'name', label: 'Имя', type: 'text', placeholder: 'Имя пользователя' },
              { field: 'email', label: 'Email', type: 'email', placeholder: 'email@example.com' },
              { field: 'password', label: 'Пароль', type: 'password', placeholder: 'Минимум 6 символов' },
            ].map(({ field, label, type, placeholder }) => (
              <div key={field}>
                <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
                <input type={type} value={(form as any)[field]} placeholder={placeholder}
                  onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
                  required={field !== 'name'} minLength={field === 'password' ? 6 : undefined}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400" />
              </div>
            ))}
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          {success && <p className="text-green-600 text-sm">{success}</p>}
          <button type="submit" disabled={saving}
            className="bg-yellow-400 hover:bg-yellow-500 text-black text-sm font-semibold px-5 py-2 rounded-xl transition disabled:opacity-50">
            {saving ? 'Создание...' : 'Создать аккаунт'}
          </button>
        </form>
      )}

      {success && !showForm && <p className="text-green-600 text-sm mb-3">{success}</p>}
      {error && !showForm && <p className="text-red-500 text-sm mb-3">{error}</p>}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              {['Имя', 'Email', 'Статус', 'Дата создания'].map(h => (
                <th key={h} className="text-left px-4 py-3 font-medium text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">Загрузка...</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">Нет пользователей</td></tr>
            ) : users.map(u => (
              <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-900">{u.name || '-'}</td>
                <td className="px-4 py-3 text-gray-600">{u.email}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    {u.is_active ? 'Активен' : 'Неактивен'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{new Date(u.created_at).toLocaleDateString('ru-RU')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Orders section ─────────────────────────────────────────────────────────────
function OrdersSection() {
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getOrders().then((res: any) => setOrders(res.data || [])).catch(() => setOrders([])).finally(() => setLoading(false))
  }, [])

  const STATUS_COLOR: Record<string, string> = {
    paid: 'bg-green-100 text-green-700',
    pending: 'bg-yellow-100 text-yellow-700',
    cancelled: 'bg-red-100 text-red-700',
    refunded: 'bg-orange-100 text-orange-700',
    picked_up: 'bg-blue-100 text-blue-700',
  }
  const STATUS_LABEL: Record<string, string> = {
    paid: 'Оплачен', pending: 'Ожидание', cancelled: 'Отменён', refunded: 'Возврат', picked_up: 'Получен',
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold text-gray-900">Заказы</h2>
        <span className="text-sm text-gray-500">{loading ? '' : `${orders.length} заказов`}</span>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="py-10 text-center text-gray-400">Загрузка...</div>
        ) : orders.length === 0 ? (
          <div className="py-10 text-center text-gray-400">Нет заказов</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                {['ID', 'Набор', 'Сумма', 'Статус', 'Дата'].map(h => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {orders.map((o, idx) => (
                <tr key={o.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{o.id?.slice(0, 8)}...</td>
                  <td className="px-4 py-3 text-gray-900">{o.combo_title || o.combo_id || '-'}</td>
                  <td className="px-4 py-3 font-semibold text-gray-900">{o.amount ? `${o.amount} ₽` : '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[o.status] || 'bg-gray-100 text-gray-600'}`}>
                      {STATUS_LABEL[o.status] || o.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{new Date(o.created_at).toLocaleDateString('ru-RU')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// ── Combos section ─────────────────────────────────────────────────────────────
function CombosSection() {
  const [combos, setCombos] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getCombos().then((res: any) => setCombos(res.data || [])).catch(() => setCombos([])).finally(() => setLoading(false))
  }, [])

  const STATUS_COLOR: Record<string, string> = {
    available: 'bg-green-100 text-green-700',
    draft: 'bg-gray-100 text-gray-600',
    sold: 'bg-blue-100 text-blue-700',
    expired: 'bg-orange-100 text-orange-700',
    cancelled: 'bg-red-100 text-red-700',
    ready: 'bg-yellow-100 text-yellow-700',
  }
  const STATUS_LABEL: Record<string, string> = {
    available: 'В продаже', draft: 'Черновик', sold: 'Продан', expired: 'Истёк', cancelled: 'Отменён', ready: 'Готов',
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold text-gray-900">Наборы</h2>
        <span className="text-sm text-gray-500">{loading ? '' : `${combos.length} наборов`}</span>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="py-10 text-center text-gray-400">Загрузка...</div>
        ) : combos.length === 0 ? (
          <div className="py-10 text-center text-gray-400">Нет наборов</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                {['Название', 'Магазин', 'Цена', 'Скидка', 'Статус'].map(h => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {combos.map(c => (
                <tr key={c.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-3 font-semibold text-gray-900">{c.title}</td>
                  <td className="px-4 py-3 text-gray-600">{c.shop_name || '-'}</td>
                  <td className="px-4 py-3 text-gray-900">{c.sale_price} ₽</td>
                  <td className="px-4 py-3 text-green-600 font-semibold">-{c.discount_rate}%</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[c.status] || 'bg-gray-100 text-gray-600'}`}>
                      {STATUS_LABEL[c.status] || c.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// ── Lockers section ────────────────────────────────────────────────────────────
function LockersSection() {
  const [lockers, setLockers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getLockers().then((res: any) => setLockers(res.data || [])).catch(() => setLockers([])).finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold text-gray-900">Постаматы</h2>
        <span className="text-sm text-gray-500">{loading ? '' : `${lockers.length} постаматов`}</span>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="py-10 text-center text-gray-400">Загрузка...</div>
        ) : lockers.length === 0 ? (
          <div className="py-10 text-center text-gray-400">Нет постаматов</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                {['Название', 'Адрес', 'Ячеек', 'Свободно', 'Занято'].map(h => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {lockers.map(loc => {
                const total = loc.units?.length || 0
                const free = loc.units?.filter((u: any) => u.status === 'AVAILABLE').length || 0
                const occupied = loc.units?.filter((u: any) => u.status === 'OCCUPIED' || u.status === 'RESERVED').length || 0
                return (
                  <tr key={loc.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="px-4 py-3 font-semibold text-gray-900">{loc.name}</td>
                    <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{loc.address || '-'}</td>
                    <td className="px-4 py-3 text-gray-900">{total}</td>
                    <td className="px-4 py-3 text-green-600 font-semibold">{free}</td>
                    <td className="px-4 py-3 text-orange-600 font-semibold">{occupied}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// ── Analytics section ──────────────────────────────────────────────────────────
function AnalyticsSection() {
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getSalesSummary().then((res: any) => setSummary(res?.data ?? res)).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const stats = [
    { label: 'Выручка', value: summary?.total_revenue ? `${Math.round(summary.total_revenue).toLocaleString('ru')} ₽` : '—', color: 'text-yellow-600' },
    { label: 'Заказов продано', value: summary?.total_orders ?? '—', color: 'text-blue-600' },
    { label: 'Еды спасено', value: summary?.food_saved_kg ? `${summary.food_saved_kg.toFixed(1)} кг` : '—', color: 'text-green-600' },
    { label: 'CO₂ сохранено', value: summary?.co2_saved_kg ? `${summary.co2_saved_kg.toFixed(1)} кг` : '—', color: 'text-emerald-600' },
  ]

  return (
    <div>
      <h2 className="text-lg font-bold text-gray-900 mb-4">Аналитика платформы</h2>
      {loading ? (
        <div className="text-center py-10 text-gray-400">Загрузка...</div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {stats.map(s => (
              <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-5">
                <div className={`text-2xl font-extrabold ${s.color} leading-none mb-1`}>{s.value}</div>
                <div className="text-sm text-gray-500">{s.label}</div>
              </div>
            ))}
          </div>
          {!summary && (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
              Нет данных аналитики
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ── Main admin page ────────────────────────────────────────────────────────────
export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<NavTab>('users')

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Панель администратора</h1>

      {/* Navigation */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-6 overflow-x-auto">
        {NAV_TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium transition whitespace-nowrap ${activeTab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'users' && <UsersSection />}
      {activeTab === 'orders' && <OrdersSection />}
      {activeTab === 'combos' && <CombosSection />}
      {activeTab === 'lockers' && <LockersSection />}
      {activeTab === 'analytics' && <AnalyticsSection />}
    </div>
  )
}
