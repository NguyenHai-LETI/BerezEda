'use client'
import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { Lock, ShoppingBasket, Store, MapPin } from 'lucide-react'
import { getLocker, getCombos, getLockerShops, addFavoriteLocker } from '@/lib/api'
import { API_URL } from '@/lib/constants'

function imgUrl(path?: string | null) {
  if (!path) return null
  if (path.startsWith('http')) return path
  const base = API_URL.replace(/\/api\/?$/, '')
  return `${base}/uploads/${path.replace(/^\//, '')}`
}

export default function LockerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [locker, setLocker] = useState<any>(null)
  const [combos, setCombos] = useState<any[]>([])
  const [shops, setShops] = useState<any[]>([])
  const [tab, setTab] = useState<'combos' | 'shops'>('combos')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [l, c, s] = await Promise.all([
          getLocker(id),
          getCombos({ locker_location_id: id }),
          getLockerShops(id),
        ])
        setLocker(l.data)
        setCombos(c.data || [])
        setShops(s.data || [])
      } catch {}
      setLoading(false)
    }
    load()
  }, [id])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-400"/></div>
  if (!locker) return <div className="p-4 text-center text-gray-500">Ячейка не найдена</div>

  const lockerImg = imgUrl(locker.image)

  return (
    <div className="max-w-2xl mx-auto">
      {/* Hero */}
      <div className="bg-teal-600 text-white relative overflow-hidden">
        {lockerImg && (
          <div className="absolute inset-0">
            <Image src={lockerImg} alt={locker.name} fill className="object-cover" unoptimized />
            <div className="absolute inset-0 bg-slate-700/65" />
          </div>
        )}
        <div className="relative p-6 pt-12">
          {lockerImg ? (
            <div className="w-[104px] h-[104px] rounded-xl overflow-hidden mb-3 border-2 border-white/30">
              <Image src={lockerImg} alt={locker.name} width={104} height={104} className="object-cover w-full h-full" unoptimized />
            </div>
          ) : (
            <Lock className="h-10 w-10 text-teal-200 mb-3" aria-hidden="true" />
          )}
          <h1 className="text-xl font-bold">{locker.name}</h1>
          <p className="text-teal-100 text-sm mt-1">{locker.description}</p>
          <p className="text-teal-200 text-xs mt-2 flex items-center gap-1"><MapPin className="h-3 w-3 flex-shrink-0" aria-hidden="true" /> {locker.address}</p>
          <div className="flex items-center gap-4 mt-3 text-sm">
            <span className="bg-white/20 rounded-full px-3 py-1">
              Боксов: {locker.units?.length || 0}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 px-4">
        <button
          onClick={() => setTab('combos')}
          className={`px-4 py-3 text-sm font-medium border-b-2 transition ${tab === 'combos' ? 'border-teal-500 text-teal-600' : 'border-transparent text-gray-500'}`}
        >
          Наборы ({combos.length})
        </button>
        <button
          onClick={() => setTab('shops')}
          className={`px-4 py-3 text-sm font-medium border-b-2 transition ${tab === 'shops' ? 'border-teal-500 text-teal-600' : 'border-transparent text-gray-500'}`}
        >
          Магазины ({shops.length})
        </button>
      </div>

      <div className="px-4 py-4 space-y-3">
        {tab === 'combos' ? (
          combos.length === 0 ? (
            <p className="text-center text-gray-400 py-8">Нет доступных наборов</p>
          ) : combos.map(combo => (
            <Link key={combo.id} href={`/combos/${combo.id}`}>
              <div className="bg-white rounded-2xl border border-gray-100 p-4 flex gap-3 hover:shadow-md transition">
                <div className="w-16 h-16 bg-gray-100 rounded-xl flex-shrink-0 flex items-center justify-center text-2xl overflow-hidden">
                  {(() => {
                    const comboImg = combo.image ? imgUrl(combo.image) : null
                    const productImg = combo.products?.find((p: any) => p.product_image)?.product_image
                    const thumb = comboImg || (productImg ? imgUrl(productImg) : null)
                    return thumb ? <img src={thumb} alt={combo.title} className="w-full h-full object-cover" /> : <ShoppingBasket className="h-6 w-6 text-gray-400" aria-hidden="true" />
                  })()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900">{combo.title}</p>
                  <p className="text-yellow-500 font-bold mt-1">{combo.sale_price.toLocaleString('ru-RU')} ₽</p>
                  <p className="text-xs text-gray-400 line-through">{combo.original_price.toLocaleString('ru-RU')} ₽</p>
                </div>
                <div className="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full h-fit">-{combo.discount_rate}%</div>
              </div>
            </Link>
          ))
        ) : (
          shops.length === 0 ? (
            <p className="text-center text-gray-400 py-8">Нет магазинов</p>
          ) : shops.map((shop: any) => (
            <Link key={shop.id} href={`/shops/${shop.id}`}>
              <div className="bg-white rounded-2xl border border-gray-100 p-4 flex gap-3 hover:shadow-md transition">
                <div className="w-14 h-14 bg-gray-100 rounded-xl flex-shrink-0 flex items-center justify-center text-2xl overflow-hidden">
                  {(() => {
                    const shopImg = imgUrl(shop.image || shop.logo)
                    return shopImg ? <img src={shopImg} alt={shop.name} className="w-full h-full object-cover" /> : <Store className="h-6 w-6 text-gray-400" aria-hidden="true" />
                  })()}
                </div>
                <div>
                  <p className="font-medium text-gray-900">{shop.name}</p>
                  {shop.description && <p className="text-sm text-gray-500 mt-0.5 line-clamp-1">{shop.description}</p>}
                  {shop.address && <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1"><MapPin className="h-3 w-3 flex-shrink-0" aria-hidden="true" /> {shop.address}</p>}
                </div>
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  )
}
