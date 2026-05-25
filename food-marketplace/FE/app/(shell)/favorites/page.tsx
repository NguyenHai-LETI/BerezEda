"use client";

import { useEffect, useState } from "react";
import { Heart, Loader2, Store, MapPin, Search } from "lucide-react";
import { getFavoriteShops, removeFavoriteShop, getCombos } from "@/lib/api";
import { API_URL } from "@/lib/constants";

function imgUrl(path?: string | null) {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  const base = API_URL.replace(/\/api\/?$/, "");
  return `${base}/uploads/${path.replace(/^\//, "")}`;
}

export default function FavoritesPage() {
  const [shops, setShops] = useState<any[]>([]);
  const [activeCombosByShop, setActiveCombosByShop] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'all' | 'active'>('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    Promise.all([getFavoriteShops(), getCombos()])
      .then(([favRes, comboRes]) => {
        setShops(favRes.data || []);
        const combos: any[] = comboRes.data || [];
        const now = new Date();
        const counts: Record<string, number> = {};
        combos.forEach(c => {
          const end = c.sale_end_time
            ? new Date(c.sale_end_time.endsWith('Z') ? c.sale_end_time : c.sale_end_time + 'Z')
            : null;
          if (end && end > now && c.shop_id) {
            counts[c.shop_id] = (counts[c.shop_id] || 0) + 1;
          }
        });
        setActiveCombosByShop(counts);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleUnfavorite(shopId: string) {
    try {
      await removeFavoriteShop(shopId);
      setShops((prev) => prev.filter((s) => (s.id || s.shop_id) !== shopId));
    } catch {}
  }

  const filtered = shops.filter(s => {
    const name = (s.name || '').toLowerCase();
    const q = search.toLowerCase();
    if (!name.includes(q)) return false;
    if (tab === 'active') return (activeCombosByShop[s.id || s.shop_id] || 0) > 0;
    return true;
  });

  const tabCounts = {
    all: shops.length,
    active: shops.filter(s => (activeCombosByShop[s.id || s.shop_id] || 0) > 0).length,
  };

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-5 w-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-1 bg-line/60 rounded-[8px] p-0.5">
          {([['all', 'Все'], ['active', 'С наборами']] as const).map(([key, lbl]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] text-sm font-semibold transition-colors ${
                tab === key ? 'bg-surface text-ink-100 shadow-sm' : 'text-ink-60 hover:text-ink-100'
              }`}
            >
              {lbl}
              <span className={`text-[11px] px-1.5 py-0.5 rounded-full ${tab === key ? 'bg-line text-ink-60' : 'text-ink-40'}`}>
                {tabCounts[key]}
              </span>
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 bg-surface border border-line rounded-[10px] px-3 py-2 w-52">
          <Search className="h-3.5 w-3.5 text-ink-40 shrink-0" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Поиск магазинов..."
            className="flex-1 text-sm text-ink-100 placeholder-ink-40 bg-transparent outline-none min-w-0"
          />
        </div>
      </div>

      {/* List */}
      <section className="bg-surface rounded-card shadow-sm">
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-ink-40" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center py-16 text-ink-40">
            <Heart className="h-12 w-12 mb-4 text-line2" />
            <p className="font-medium text-sm">
              {search ? 'Ничего не найдено' : 'Нет избранных магазинов'}
            </p>
            {!search && <p className="text-xs mt-1">Добавьте магазин в избранное на странице набора</p>}
          </div>
        ) : (
          <div className="divide-y divide-line">
            {filtered.map(shop => {
              const shopId = shop.id || shop.shop_id;
              const shopImg = imgUrl(shop.image || shop.logo);
              const setsCount = activeCombosByShop[shopId] || 0;
              return (
                <div key={shopId} className="flex items-center gap-4 p-4 hover:bg-bg/50 transition-colors">
                  {/* Avatar */}
                  <div className="w-16 h-16 rounded-[12px] bg-line/60 overflow-hidden flex items-center justify-center shrink-0">
                    {shopImg
                      ? <img src={shopImg} alt={shop.name} className="w-full h-full object-cover" />
                      : <Store className="h-6 w-6 text-ink-40" />
                    }
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-bold text-ink-100 truncate">{shop.name}</span>
                      {shop.rating && (
                        <span className="text-[11px] text-warn font-semibold shrink-0">★ {shop.rating}</span>
                      )}
                    </div>
                    {shop.description && (
                      <div className="text-xs text-ink-60 truncate mb-0.5">{shop.description}</div>
                    )}
                    {shop.address && (
                      <div className="flex items-center gap-1 text-[11px] text-ink-40 truncate">
                        <MapPin className="h-3 w-3 shrink-0" />
                        <span className="truncate">{shop.address}</span>
                      </div>
                    )}
                  </div>

                  {/* Sets badge */}
                  <div className="shrink-0">
                    {setsCount > 0
                      ? <span className="text-[11px] px-2 py-1 rounded-full bg-eco-soft text-eco font-semibold">{setsCount} наборов</span>
                      : <span className="text-[11px] px-2 py-1 rounded-full bg-line text-ink-40">нет наборов</span>
                    }
                  </div>

                  {/* Heart */}
                  <button
                    onClick={() => handleUnfavorite(shopId)}
                    className="w-9 h-9 rounded-full flex items-center justify-center hover:bg-accent-soft transition-colors shrink-0"
                    aria-label="Убрать из избранного"
                  >
                    <Heart className="h-5 w-5 fill-accent text-accent" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
