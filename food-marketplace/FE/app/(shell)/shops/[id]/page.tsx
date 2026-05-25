'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { Store, Star, MapPin, Package } from 'lucide-react'
import { getShop, getCombos, getFavoriteShops, addFavoriteShop, removeFavoriteShop } from '@/lib/api'
import { API_URL } from '@/lib/constants'
import { CountdownBadge } from '@/components/CountdownBadge'

function imgUrl(path?: string | null): string | null {
  if (!path) return null
  if (path.startsWith('http')) return path
  const base = API_URL.replace(/\/api\/?$/, '')
  return `${base}/uploads/${path.replace(/^\//, '')}`
}

function remainingSecs(saleEndTime?: string): number {
  if (!saleEndTime) return 0
  const end = new Date(saleEndTime.endsWith('Z') ? saleEndTime : saleEndTime + 'Z')
  return Math.max(0, Math.floor((end.getTime() - Date.now()) / 1000))
}

export default function ShopDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [shop, setShop] = useState<any>(null)
  const [combos, setCombos] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [fav, setFav] = useState(false)
  const [favId, setFavId] = useState<string | null>(null)
  const [favLoading, setFavLoading] = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const [shopRes, combosRes, favRes] = await Promise.all([
          getShop(id),
          getCombos({ shop_id: id }),
          getFavoriteShops().catch(() => ({ data: [] })),
        ])
        const shopData = shopRes.data || shopRes
        setShop(shopData)
        setCombos(combosRes.data || [])

        const favShops: any[] = (favRes as any).data || []
        const found = favShops.find((f: any) => f.shop_id === id || f.id === id)
        if (found) { setFav(true); setFavId(found.id || id) }
      } catch {}
      setLoading(false)
    }
    load()
  }, [id])

  async function toggleFav() {
    if (favLoading) return
    setFavLoading(true)
    try {
      if (fav && favId) {
        await removeFavoriteShop(favId)
        setFav(false); setFavId(null)
      } else {
        const res: any = await addFavoriteShop(id)
        setFav(true)
        setFavId(res?.data?.id || id)
      }
    } catch {} finally { setFavLoading(false) }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )

  if (!shop) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="text-ink-60 mb-4">Магазин не найден</p>
        <Link href="/" className="text-primary font-semibold hover:underline">На главную</Link>
      </div>
    )
  }

  const shopImg = shop.image ? imgUrl(shop.image) : null
  const availableCombos = combos.filter(c => c.status === 'available')

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-5 max-w-[720px] mx-auto w-full">
      {/* Shop hero card */}
      <section className="bg-surface rounded-card shadow-sm overflow-hidden">
        <div className="relative h-40 bg-line/50">
          {shopImg ? (
            <Image src={shopImg} alt={shop.name} fill className="object-cover" unoptimized />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <Store className="h-12 w-12 text-line2" />
            </div>
          )}
        </div>
        <div className="p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h1 className="text-xl font-bold text-ink-100">{shop.name}</h1>
              {shop.description && <p className="text-sm text-ink-60 mt-1">{shop.description}</p>}
              <div className="flex items-center gap-3 mt-2 flex-wrap">
                {shop.rating != null && (
                  <div className="flex items-center gap-1 text-sm font-semibold text-ink-100">
                    <Star className="h-4 w-4 fill-primary stroke-primary" />
                    <span>{Number(shop.rating).toFixed(1)}</span>
                    {shop.review_count > 0 && <span className="text-ink-40 font-normal">({shop.review_count})</span>}
                  </div>
                )}
                {shop.address && (
                  <div className="flex items-center gap-1 text-xs text-ink-40">
                    <MapPin className="h-3.5 w-3.5" />
                    <span>{shop.address}</span>
                  </div>
                )}
              </div>
            </div>
            <button
              onClick={toggleFav}
              disabled={favLoading}
              className="shrink-0 text-sm font-semibold px-3 py-1.5 rounded-[10px] border border-line hover:bg-line/60 transition-colors disabled:opacity-50"
              style={{ color: fav ? '#E8553D' : '#8a8a8a', borderColor: fav ? '#E8553D' : undefined }}
            >
              {fav ? '♥ В избранном' : '♡ В избранное'}
            </button>
          </div>
        </div>
      </section>

      {/* Combos section */}
      <section className="bg-surface rounded-card shadow-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-[11px] font-semibold text-ink-40 uppercase tracking-wider mb-0.5">Наборы магазина</div>
            <h3 className="text-base font-bold text-ink-100">
              {availableCombos.length} {availableCombos.length === 1 ? 'набор' : availableCombos.length < 5 ? 'набора' : 'наборов'} в продаже
            </h3>
          </div>
        </div>

        {combos.length === 0 ? (
          <div className="flex flex-col items-center py-10 gap-3 text-center">
            <Package className="h-10 w-10 text-line2" />
            <p className="font-semibold text-ink-60">Нет доступных наборов</p>
            <p className="text-xs text-ink-40">Следите за появлением новых предложений</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {availableCombos.map(combo => {
              const comboImg = combo.image ? imgUrl(combo.image) : null
              const productImg = combo.products?.find((p: any) => p.product_image)?.product_image
              const thumb = comboImg || (productImg ? imgUrl(productImg) : null)
              return (
                <Link key={combo.id} href={`/combos/${combo.id}`} className="group block">
                  <div className="rounded-card border border-line bg-surface hover:shadow-md transition-shadow overflow-hidden">
                    <div className="relative w-full aspect-[4/3]">
                      <div className="absolute inset-0 bg-line/50">
                        {thumb && <Image src={thumb} alt={combo.title} fill className="object-cover" unoptimized />}
                      </div>
                      <span className="absolute top-2.5 left-2.5 bg-accent text-white text-[11px] font-bold px-2 py-0.5 rounded-full">
                        −{combo.discount_rate}%
                      </span>
                      {combo.sale_end_time && (
                        <div className="absolute top-2.5 right-2.5">
                          <CountdownBadge seconds={remainingSecs(combo.sale_end_time)} className="bg-black/60 text-white text-[11px]" />
                        </div>
                      )}
                    </div>
                    <div className="p-3">
                      <div className="text-sm font-bold text-ink-100 truncate mb-1">{combo.title}</div>
                      <div className="flex items-baseline gap-1.5 mb-2">
                        <span className="text-base font-extrabold text-ink-100">{combo.sale_price?.toLocaleString('ru-RU')} ₽</span>
                        <span className="text-xs text-ink-40 line-through">{combo.original_price?.toLocaleString('ru-RU')} ₽</span>
                      </div>
                      {combo.locker_info && (
                        <div className="flex items-center gap-1 text-[11px] text-ink-40 truncate">
                          <MapPin className="h-3 w-3 shrink-0" />
                          <span className="truncate">{combo.locker_info.locker_name}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
