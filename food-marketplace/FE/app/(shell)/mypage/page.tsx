"use client";

import Link from "next/link";
import { ChevronRight, User, Bell, Star, CreditCard, FileText, Phone, Edit2, Globe } from "lucide-react";
import { getUser } from "@/lib/auth";
import { useI18n } from "@/contexts/I18nContext";

export default function MyPage() {
  const user = getUser();
  const { t } = useI18n();

  const initials = user?.name
    ? user.name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() ?? '?';

  const menuItems = [
    { icon: User,       label: t('mypage.account'),       href: "/mypage/account" },
    { icon: Bell,       label: t('mypage.notifications'), href: "/mypage/notifications" },
    { icon: Star,       label: t('mypage.my_reviews'),    href: "/mypage/reviews" },
    { icon: Globe,      label: t('mypage.language'),      href: "/mypage/language" },
    { icon: CreditCard, label: t('mypage.payment'),       href: "/mypage/payment" },
    { icon: FileText,   label: t('mypage.privacy'),       href: "/mypage/privacy" },
    { icon: FileText,   label: t('mypage.terms'),         href: "/mypage/terms" },
    { icon: Phone,      label: t('mypage.contact'),       href: "/mypage/contact" },
  ];

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-5 max-w-[640px] mx-auto w-full">
      {/* Profile hero */}
      <section className="bg-surface rounded-card shadow-sm p-6 flex items-center gap-5">
        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-eco to-[#4CAF85] flex items-center justify-center text-white text-xl font-extrabold shrink-0">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-bold text-ink-100 leading-tight truncate">{user?.name ?? t('nav.profile')}</h3>
          <p className="text-sm text-ink-40 truncate">{user?.email ?? ''}</p>
          <div className="flex flex-wrap gap-2 mt-2">
            <span className="text-[11px] px-2 py-1 rounded-full bg-eco-soft text-eco font-semibold">{t('mypage.saved_combos')}</span>
            <span className="text-[11px] px-2 py-1 rounded-full bg-primary-soft text-ink-60 font-semibold">{t('mypage.reviews_badge')}</span>
          </div>
        </div>
        <Link
          href="/mypage/account"
          className="flex items-center gap-1.5 text-sm font-semibold text-ink-60 border border-line rounded-[10px] px-3 py-2 hover:bg-line/60 transition-colors shrink-0"
        >
          <Edit2 className="h-3.5 w-3.5" />
          {t('mypage.edit')}
        </Link>
      </section>

      {/* Menu */}
      <section className="bg-surface rounded-card shadow-sm overflow-hidden">
        <div className="divide-y divide-line">
          {menuItems.map((item, index) => {
            const Icon = item.icon;
            return (
              <Link
                key={index}
                href={item.href}
                className="flex items-center gap-4 px-4 py-3.5 hover:bg-bg/60 transition-colors"
              >
                <div className="w-8 h-8 rounded-[8px] bg-line/60 flex items-center justify-center shrink-0">
                  <Icon className="h-[16px] w-[16px] text-ink-60" />
                </div>
                <span className="text-sm font-semibold text-ink-100 flex-1">{item.label}</span>
                <ChevronRight className="h-4 w-4 text-ink-40 shrink-0" />
              </Link>
            );
          })}
        </div>
      </section>

      {/* Footer */}
      <div className="px-1">
        <span className="text-xs text-ink-40">{t('mypage.version')} 1.0.18 (420)</span>
      </div>
    </div>
  );
}
