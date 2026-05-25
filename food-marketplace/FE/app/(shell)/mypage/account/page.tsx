'use client'

import { useEffect, useRef, useState } from 'react'
import { Camera } from 'lucide-react'
import { getMe, updateMe, uploadAvatar } from '@/lib/api'

interface UserProfile {
  id: string
  name?: string
  email: string
  phone?: string
  birthday?: string
  gender?: string
  icon?: string
  role: string
}

const genderLabel = (g?: string) => ({ male: 'Мужской', female: 'Женский', other: 'Другой' }[g || ''] || '—')

function InfoRow({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex items-center justify-between px-5 py-3.5">
      <span className="text-sm text-ink-40">{label}</span>
      <span className="text-sm font-semibold text-ink-100">{value || '—'}</span>
    </div>
  )
}

export default function AccountPage() {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ name: '', phone: '', birthday: '', gender: '' })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [uploadingAvatar, setUploadingAvatar] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    getMe()
      .then((r: any) => {
        const u = r.data
        setUser(u)
        setForm({
          name: u.name || '',
          phone: u.phone || '',
          birthday: u.birthday ? u.birthday.slice(0, 10) : '',
          gender: u.gender || '',
        })
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function handleAvatarChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadingAvatar(true)
    setError('')
    setSuccess('')
    try {
      const r: any = await uploadAvatar(file)
      if (r?.data) setUser(r.data)
      setSuccess('Фото обновлено')
    } catch (err: any) {
      setError(err.message || 'Ошибка загрузки фото')
    } finally {
      setUploadingAvatar(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function handleSave() {
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      const payload: Record<string, string> = {}
      if (form.name) payload.name = form.name
      if (form.phone) payload.phone = form.phone
      if (form.birthday) payload.birthday = form.birthday
      if (form.gender) payload.gender = form.gender
      const r: any = await updateMe(payload)
      setUser(r.data)
      setEditing(false)
      setSuccess('Профиль обновлён')
    } catch (e: any) {
      setError(e.message || 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )

  const avatarUrl = user?.icon
    ? (user.icon.startsWith('http') ? user.icon : `${process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') || 'http://localhost:8000'}${user.icon}`)
    : null

  const initials = user?.name
    ? user.name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() ?? '?'

  const inputCls = "w-full border border-line rounded-[10px] px-4 py-2.5 text-sm text-ink-100 bg-bg focus:outline-none focus:ring-2 focus:ring-primary/40"
  const labelCls = "text-xs font-semibold text-ink-40 block mb-1"

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-5 max-w-[540px] mx-auto w-full">
      {/* Avatar card */}
      <section className="bg-surface rounded-card shadow-sm p-8 flex flex-col items-center">
        <div className="relative mb-4">
          {avatarUrl ? (
            <img src={avatarUrl} alt="avatar" className="w-[88px] h-[88px] rounded-full object-cover border-4 border-primary-soft" />
          ) : (
            <div className="w-[88px] h-[88px] rounded-full bg-gradient-to-br from-eco to-[#4CAF85] flex items-center justify-center text-white text-2xl font-extrabold border-4 border-eco-soft">
              {initials}
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleAvatarChange}
          />
          <button
            className="absolute bottom-0 right-0 w-7 h-7 rounded-full bg-ink-100 flex items-center justify-center disabled:opacity-50"
            aria-label="Сменить фото"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadingAvatar}
          >
            <Camera className="h-3.5 w-3.5 text-white" />
          </button>
        </div>
        <h3 className="text-lg font-bold text-ink-100">{user?.name || '—'}</h3>
        <p className="text-sm text-ink-40">{user?.email}</p>
      </section>

      {/* Fields */}
      <section className="bg-surface rounded-card shadow-sm overflow-hidden">
        {editing ? (
          <div className="p-5 space-y-4">
            <div>
              <label className={labelCls}>Имя</label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Введите имя" />
            </div>
            <div>
              <label className={labelCls}>Телефон</label>
              <input value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} className={inputCls} placeholder="+7 ..." />
            </div>
            <div>
              <label className={labelCls}>Дата рождения</label>
              <input type="date" value={form.birthday} onChange={e => setForm(f => ({ ...f, birthday: e.target.value }))} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Пол</label>
              <select value={form.gender} onChange={e => setForm(f => ({ ...f, gender: e.target.value }))} className={inputCls}>
                <option value="">Не указан</option>
                <option value="male">Мужской</option>
                <option value="female">Женский</option>
                <option value="other">Другой</option>
              </select>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-line">
            <InfoRow label="Имя" value={user?.name} />
            <InfoRow label="Email" value={user?.email} />
            <InfoRow label="Телефон" value={user?.phone} />
            <InfoRow label="Дата рождения" value={user?.birthday ? new Date(user.birthday).toLocaleDateString('ru-RU') : undefined} />
            <InfoRow label="Пол" value={genderLabel(user?.gender)} />
          </div>
        )}
      </section>

      {error && <p className="text-accent text-sm text-center">{error}</p>}
      {success && <p className="text-eco text-sm text-center">{success}</p>}

      {editing ? (
        <div className="flex gap-3">
          <button
            onClick={() => setEditing(false)}
            className="flex-1 border-2 border-line text-ink-60 font-semibold py-3 rounded-[10px] hover:bg-line/60 transition-colors"
          >
            Отмена
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 bg-primary hover:bg-primary-hover disabled:opacity-50 text-ink-100 font-bold py-3 rounded-[10px] transition-colors"
          >
            {saving ? 'Сохранение...' : 'Сохранить'}
          </button>
        </div>
      ) : (
        <button
          onClick={() => setEditing(true)}
          className="w-full bg-primary hover:bg-primary-hover text-ink-100 font-bold py-3 rounded-[10px] transition-colors"
        >
          Редактировать профиль
        </button>
      )}
    </div>
  )
}
