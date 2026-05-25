'use client';
import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { getUser, logout, AuthUser } from '@/lib/auth';
import { getMyShop } from '@/lib/api';
import {
  LayoutDashboard, Plus, ClipboardList, TrendingUp, Bell,
  Package, Coffee, Settings, LogOut, ChevronDown, Globe, LucideIcon, PanelLeft,
} from 'lucide-react';
import { useI18n } from '@/contexts/I18nContext';
import { LOCALES, LOCALE_NAMES, type Locale } from '@/lib/i18n';
import { cn } from '@/lib/utils';

interface NavItem {
  href: string
  labelKey: string
  icon: LucideIcon
  exact?: boolean
  accent?: boolean
}

const MAIN_NAV_DEF: NavItem[] = [
  { href: '/seller', labelKey: 'seller.nav.home', icon: LayoutDashboard, exact: true },
  { href: '/seller/add-item', labelKey: 'seller.nav.add_item', icon: Plus, accent: true },
  { href: '/seller/sales-history', labelKey: 'seller.nav.sales_history', icon: ClipboardList },
  { href: '/seller/revenue', labelKey: 'seller.nav.revenue', icon: TrendingUp },
  { href: '/seller/notifications', labelKey: 'seller.nav.notifications', icon: Bell },
];

const EXTRA_NAV_DEF: NavItem[] = [
  { href: '/seller/items', labelKey: 'seller.nav.my_items', icon: Package },
  { href: '/seller/product-management', labelKey: 'seller.nav.products', icon: Coffee },
  { href: '/seller/profile-settings', labelKey: 'seller.nav.settings', icon: Settings },
];

const ALL_NAV_DEF: NavItem[] = [...MAIN_NAV_DEF, ...EXTRA_NAV_DEF];

function isActive(href: string, pathname: string, exact = false) {
  if (exact) return pathname === href;
  return pathname === href || pathname.startsWith(href + '/');
}

export default function SellerLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { t, locale, setLocale } = useI18n();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [shopName, setShopName] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const SIDEBAR_W = collapsed ? 72 : 256;

  useEffect(() => {
    const u = getUser();
    const token = localStorage.getItem('access_token');
    if (!u || !token) { router.replace('/login'); return; }
    if (!['owner_shop', 'admin'].includes(u.role)) { router.replace('/'); return; }
    setUser(u);
    setReady(true);
    getMyShop().then(r => { if (r?.data?.name) setShopName(r.data.name); }).catch(() => {});
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!ready) return (
    <div className="flex items-center justify-center h-screen bg-bg">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  );

  const displayName = shopName ?? user?.name ?? '';
  const initials = (displayName || 'U').slice(0, 2).toUpperCase();

  const activeItem = ALL_NAV_DEF.find(n =>
    n.exact ? pathname === n.href : (pathname === n.href || pathname.startsWith(n.href + '/'))
  );
  const pageTitle = activeItem ? t(activeItem.labelKey) : t('seller.cabinet');

  return (
    <div className="min-h-screen bg-bg flex">

      {/* ── Sidebar ── */}
      <aside
        className="hidden md:flex flex-col fixed h-full z-20 overflow-hidden transition-all duration-200"
        style={{
          width: SIDEBAR_W,
          background: '#ffffff',
          borderRight: '1px solid #ececea',
          padding: collapsed ? '22px 8px' : '22px 16px',
        }}
      >
        {/* Brand */}
        <div className="flex items-center pb-4" style={{ borderBottom: '1px solid #ececea', gap: collapsed ? 0 : 10 }}>
          <div
            className="grid place-items-center font-extrabold flex-shrink-0"
            style={{ width: 36, height: 36, background: '#FFC629', color: '#1a1a1a', fontSize: 16, borderRadius: 10 }}
          >
            Б
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0 pl-1">
              <div className="font-extrabold" style={{ fontSize: 16, letterSpacing: '-0.01em', lineHeight: 1.1 }}>
                БережЕда
              </div>
              <div className="font-bold uppercase" style={{ fontSize: 10.5, color: '#8a8a8a', letterSpacing: '0.14em', marginTop: 2 }}>
                {t('seller.role')}
              </div>
            </div>
          )}
          <button
            onClick={() => setCollapsed(c => !c)}
            title={collapsed ? 'Развернуть' : 'Свернуть'}
            style={{ marginLeft: collapsed ? 'auto' : undefined, marginRight: collapsed ? 'auto' : undefined }}
            className="p-1.5 rounded-[8px] text-ink-40 hover:text-ink-100 hover:bg-line transition-colors shrink-0 mt-1"
          >
            <PanelLeft
              size={16}
              style={{ transform: collapsed ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
            />
          </button>
        </div>

        {/* Main nav */}
        <nav className="flex flex-col gap-0.5 flex-1 overflow-y-auto -mx-1 px-1 pt-3">
          {MAIN_NAV_DEF.map(item => {
            const Icon = item.icon;
            const active = isActive(item.href, pathname, item.exact);
            return (
              <Link
                key={item.href}
                href={item.href}
                title={collapsed ? t(item.labelKey) : undefined}
                className="relative flex items-center gap-2.5 py-2.5 rounded-lg transition-colors"
                style={{
                  padding: '9px 10px',
                  borderRadius: 9,
                  justifyContent: collapsed ? 'center' : undefined,
                  fontWeight: active ? 700 : 500,
                  fontSize: 13.5,
                  color: active ? '#1a1a1a' : '#4a4a4a',
                  background: active ? '#FFF8E1' : 'transparent',
                  textDecoration: 'none',
                }}
                onMouseEnter={e => { if (!active) (e.currentTarget.style.background = '#f7f6f3') }}
                onMouseLeave={e => { if (!active) (e.currentTarget.style.background = 'transparent') }}
              >
                {active && !collapsed && (
                  <span
                    className="absolute rounded-sm"
                    style={{ left: -4, top: 8, bottom: 8, width: 3, background: '#FFC629', borderRadius: 3 }}
                  />
                )}
                <Icon
                  size={17}
                  strokeWidth={active ? 2.2 : 1.8}
                  style={{ color: item.accent && !active ? '#FFC629' : undefined, flexShrink: 0 }}
                />
                {!collapsed && <span className="flex-1">{t(item.labelKey)}</span>}
              </Link>
            );
          })}

          {/* Secondary nav divider */}
          <div className="my-2" style={{ height: 1, background: '#ececea' }} />

          {EXTRA_NAV_DEF.map(item => {
            const Icon = item.icon;
            const active = isActive(item.href, pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                title={collapsed ? t(item.labelKey) : undefined}
                className="relative flex items-center gap-2.5"
                style={{
                  padding: '8px 10px',
                  borderRadius: 9,
                  justifyContent: collapsed ? 'center' : undefined,
                  fontWeight: active ? 700 : 500,
                  fontSize: 13,
                  color: active ? '#1a1a1a' : '#8a8a8a',
                  background: active ? '#FFF8E1' : 'transparent',
                  textDecoration: 'none',
                }}
                onMouseEnter={e => { if (!active) { (e.currentTarget.style.background = '#f7f6f3'); (e.currentTarget.style.color = '#4a4a4a') } }}
                onMouseLeave={e => { if (!active) { (e.currentTarget.style.background = 'transparent'); (e.currentTarget.style.color = '#8a8a8a') } }}
              >
                {active && !collapsed && (
                  <span
                    className="absolute"
                    style={{ left: -4, top: 6, bottom: 6, width: 3, background: '#FFC629', borderRadius: 3 }}
                  />
                )}
                <Icon size={15} strokeWidth={1.8} style={{ flexShrink: 0 }} />
                {!collapsed && <span>{t(item.labelKey)}</span>}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* ── Content area ── */}
      <div className="flex-1 flex flex-col" id="seller-main">
        <div className="hidden md:block" style={{ marginLeft: SIDEBAR_W, transition: 'margin-left 0.2s' }}>
          {/* Topbar */}
          <header
            className="flex items-center justify-between gap-4 sticky top-0 z-10"
            style={{
              padding: '16px 32px',
              background: '#ffffff',
              borderBottom: '1px solid #ececea',
            }}
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5" style={{ fontSize: 12.5, color: '#8a8a8a', marginBottom: 4 }}>
                <span>{t('seller.cabinet')}</span>
                <span style={{ opacity: 0.5 }}>›</span>
                <span className="font-semibold" style={{ color: '#4a4a4a' }}>{pageTitle}</span>
              </div>
              <h1
                className="font-extrabold m-0 leading-none whitespace-nowrap"
                style={{ fontSize: 22, letterSpacing: '-0.02em' }}
              >
                {pageTitle}
              </h1>
            </div>

            <div className="flex items-center gap-2.5 flex-shrink-0">
              {/* Divider */}
              <div style={{ width: 1, height: 28, background: '#ececea', margin: '0 4px' }} />

              {/* User dropdown */}
              <div ref={dropdownRef} style={{ position: 'relative' }}>
                <button
                  onClick={() => setDropdownOpen(prev => !prev)}
                  className="flex items-center gap-2 transition-colors"
                  style={{
                    padding: '5px 10px 5px 5px',
                    borderRadius: 20,
                    background: dropdownOpen ? '#f7f6f3' : 'transparent',
                    border: '1px solid transparent',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={e => { (e.currentTarget.style.background = '#f7f6f3') }}
                  onMouseLeave={e => { if (!dropdownOpen) (e.currentTarget.style.background = 'transparent') }}
                >
                  <div
                    className="grid place-items-center font-bold flex-shrink-0"
                    style={{
                      width: 28, height: 28, borderRadius: 9,
                      background: 'linear-gradient(135deg, #FFC629, #f0a020)',
                      color: '#1a1a1a', fontSize: 11,
                    }}
                  >
                    {initials}
                  </div>
                  <span className="font-bold whitespace-nowrap" style={{ fontSize: 13 }}>
                    {shopName ?? user?.name ?? t('seller.default_name')}
                  </span>
                  <ChevronDown
                    size={13}
                    strokeWidth={2}
                    style={{
                      color: '#8a8a8a',
                      transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                      transition: 'transform 0.2s',
                    }}
                  />
                </button>

                {dropdownOpen && (
                  <div style={{
                    position: 'absolute',
                    right: 0,
                    top: 'calc(100% + 8px)',
                    width: 220,
                    background: '#ffffff',
                    border: '1px solid #ececea',
                    borderRadius: 12,
                    boxShadow: '0 4px 16px rgba(0,0,0,0.10)',
                    zIndex: 50,
                    overflow: 'hidden',
                  }}>
                    {/* User info */}
                    <div style={{ padding: '12px 14px', borderBottom: '1px solid #ececea', display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{
                        width: 36, height: 36, borderRadius: 9, flexShrink: 0,
                        background: 'linear-gradient(135deg, #FFC629, #f0a020)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        color: '#1a1a1a', fontSize: 13, fontWeight: 700,
                      }}>
                        {initials}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {shopName ?? user?.name ?? t('seller.default_name')}
                        </div>
                        <div style={{ fontSize: 11, color: '#8a8a8a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {user?.email ?? ''}
                        </div>
                      </div>
                    </div>

                    {/* Menu items */}
                    <div style={{ padding: '4px 0' }}>
                      <Link
                        href="/seller/profile-settings"
                        onClick={() => setDropdownOpen(false)}
                        style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 14px', fontSize: 13, color: '#1a1a1a', textDecoration: 'none' }}
                        onMouseEnter={e => { (e.currentTarget.style.background = '#f7f6f3') }}
                        onMouseLeave={e => { (e.currentTarget.style.background = 'transparent') }}
                      >
                        <Settings size={15} strokeWidth={1.8} style={{ color: '#8a8a8a', flexShrink: 0 }} />
                        {t('seller.dropdown.shop_settings')}
                      </Link>
                    </div>

                    {/* Language switcher */}
                    <div className="border-t border-line px-4 py-3">
                      <div className="flex items-center gap-2 mb-2">
                        <Globe className="h-4 w-4 text-ink-60 shrink-0" />
                        <span className="text-xs font-semibold text-ink-40 uppercase tracking-wide">{t('header.language')}</span>
                      </div>
                      <div className="flex gap-1.5">
                        {LOCALES.map(loc => (
                          <button
                            key={loc}
                            onClick={() => setLocale(loc as Locale)}
                            className={cn(
                              'flex-1 py-1.5 rounded-[8px] text-xs font-semibold transition-colors',
                              locale === loc
                                ? 'bg-primary text-ink-100'
                                : 'bg-line/60 text-ink-60 hover:bg-line hover:text-ink-100'
                            )}
                          >
                            {LOCALE_NAMES[loc as Locale]}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Logout */}
                    <div style={{ borderTop: '1px solid #ececea', padding: '4px 0' }}>
                      <button
                        onClick={() => { logout(); router.replace('/login'); }}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 10,
                          padding: '9px 14px', fontSize: 13, color: '#E8553D',
                          background: 'transparent', border: 'none', width: '100%', cursor: 'pointer',
                        }}
                        onMouseEnter={e => { (e.currentTarget.style.background = '#FFEDE7') }}
                        onMouseLeave={e => { (e.currentTarget.style.background = 'transparent') }}
                      >
                        <LogOut size={15} strokeWidth={1.8} style={{ flexShrink: 0 }} />
                        {t('header.logout')}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </header>

          {/* Page content */}
          <main className="pb-12">
            {children}
          </main>
        </div>

        {/* Mobile: no topbar, just children + bottom nav */}
        <div className="md:hidden pb-16">
          {children}
        </div>
      </div>

      {/* Mobile bottom nav */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-20 flex items-center justify-around"
        style={{
          height: 56,
          background: '#ffffff',
          borderTop: '1px solid #ececea',
        }}
        aria-label="Bottom navigation"
      >
        {MAIN_NAV_DEF.map(item => {
          const Icon = item.icon;
          const active = isActive(item.href, pathname, item.exact);
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex flex-col items-center justify-center flex-1 h-full transition-colors py-1"
              style={{ color: active ? '#FFC629' : '#8a8a8a' }}
              aria-label={t(item.labelKey)}
            >
              <Icon size={18} strokeWidth={active ? 2.2 : 1.8} />
              <span className="mt-0.5 truncate text-center" style={{ fontSize: 10, maxWidth: 56 }}>
                {t(item.labelKey).split(' ')[0]}
              </span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
