'use client'
import { useEffect, useState } from 'react'
import { Store } from 'lucide-react'
import { getMyShop, updateShop, uploadShopImage } from '@/lib/api'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
const UPLOADS_BASE = API_BASE.replace('/api', '/uploads')

function imageUrl(path?: string) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${UPLOADS_BASE}/${path}`
}

export default function SellerProfileSettings() {
  const [shop, setShop] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [shopForm, setShopForm] = useState({ name: '', description: '', address: '' })

  useEffect(() => {
    getMyShop()
      .then(s => {
        const shopData = s?.data || null
        if (shopData) {
          setShop(shopData)
          setShopForm({ name: shopData.name || '', description: shopData.description || '', address: shopData.address || '' })
        }
      })
      .catch(() => null)
      .finally(() => setLoading(false))
  }, [])

  const saveShop = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setMsg('')
    try {
      if (shop) { const u = await updateShop(shop.id, shopForm); setShop(u?.data || u) }
      setMsg('Сохранено успешно')
    } catch (err: any) { setMsg(err.message || 'Ошибка сохранения') }
    finally { setSaving(false) }
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!shop || !e.target.files?.[0]) return
    const fd = new FormData(); fd.append('file', e.target.files[0])
    try { const r = await uploadShopImage(shop.id, fd); setShop((s: any) => ({ ...s, image: r.data?.image })) } catch {}
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-400"/>
    </div>
  )

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Настройки магазина</h1>
      </div>

      {shop ? (
        <form onSubmit={saveShop} className="space-y-4">
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-xl bg-gray-100 overflow-hidden flex items-center justify-center">
                {shop.image
                  ? <img src={imageUrl(shop.image)} alt="" className="w-full h-full object-cover"/>
                  : <Store className="h-6 w-6 text-gray-400" aria-hidden="true" />}
              </div>
              <label className="cursor-pointer text-sm text-yellow-600 hover:text-yellow-700 font-medium">
                Изменить фото
                <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload}/>
              </label>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 space-y-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Название магазина</label>
              <input value={shopForm.name} onChange={e => setShopForm(f => ({ ...f, name: e.target.value }))}
                placeholder="Название вашего магазина"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-300"/>
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Описание</label>
              <textarea value={shopForm.description} onChange={e => setShopForm(f => ({ ...f, description: e.target.value }))}
                rows={3} placeholder="Расскажите о вашем магазине..."
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-300 resize-none"/>
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Адрес</label>
              <input value={shopForm.address} onChange={e => setShopForm(f => ({ ...f, address: e.target.value }))}
                placeholder="Адрес магазина"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-300"/>
            </div>
          </div>
          {msg && <div className={"text-sm px-3 py-2 rounded-lg " + (msg.includes('Ошибка') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600')}>{msg}</div>}
          <button type="submit" disabled={saving}
            className="w-full bg-yellow-400 text-white py-3 rounded-xl font-medium hover:bg-yellow-500 transition-colors disabled:opacity-50">
            {saving ? 'Сохранение...' : 'Сохранить изменения'}
          </button>
        </form>
      ) : (
        <div className="text-center py-12">
          <Store className="h-10 w-10 text-gray-300 mx-auto mb-3" aria-hidden="true" />
          <p className="text-gray-700 font-medium">Магазин ещё не создан</p>
          <p className="text-sm text-gray-500 mt-1">Обратитесь к администратору для создания магазина</p>
        </div>
      )}
    </div>
  )
}
