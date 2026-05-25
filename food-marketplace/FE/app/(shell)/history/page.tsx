"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { getOrders } from "@/lib/api";
import { ORDER_STATUS_LABELS } from "@/lib/constants";

const MONTHS_RU = [
  "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
];

const STATUS_PILL: Record<string, string> = {
  completed: "bg-eco-soft text-eco font-semibold",
  paid:       "bg-blue-50 text-blue-600 font-semibold",
  pending:    "bg-warn-soft text-warn font-semibold",
  expired:    "bg-accent-soft text-accent font-semibold",
  cancelled:  "bg-line text-ink-40 font-medium",
};

export default function HistoryPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [orders, setOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getOrders(year, month)
      .then((r) => setOrders(r.data || []))
      .catch(() => setOrders([]))
      .finally(() => setLoading(false));
  }, [year, month]);

  function prevMonth() {
    if (month === 1) { setMonth(12); setYear((y) => y - 1); }
    else setMonth((m) => m - 1);
  }
  function nextMonth() {
    const today = new Date();
    if (year === today.getFullYear() && month === today.getMonth() + 1) return;
    if (month === 12) { setMonth(1); setYear((y) => y + 1); }
    else setMonth((m) => m + 1);
  }

  const received = orders.filter(o => o.status === 'completed');
  const paid = orders.filter(o => o.status === 'paid' || o.status === 'completed');
  const totalSpent = paid.reduce((s, o) => s + (o.amount || 0), 0);
  const co2 = (received.length * 0.5).toFixed(1);

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-6 w-full">
      {/* KPI strip */}
      <div className="grid grid-cols-3 gap-4">
        {/* Spent */}
        <div className="bg-surface rounded-card shadow-sm p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="w-9 h-9 rounded-[10px] bg-primary-soft flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-[18px] h-[18px] text-ink-100" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2v20M17 7H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
              </svg>
            </div>
          </div>
          <div className="text-2xl font-extrabold text-ink-100 leading-none">
            {totalSpent.toLocaleString('ru-RU')}<span className="text-sm font-semibold text-ink-40 ml-1">₽</span>
          </div>
          <div className="text-xs text-ink-40 mt-1">Потрачено за {MONTHS_RU[month - 1].toLowerCase()}</div>
        </div>

        {/* Received */}
        <div className="bg-surface rounded-card shadow-sm p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="w-9 h-9 rounded-[10px] bg-eco-soft flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-[18px] h-[18px] text-eco" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12l5 5L20 7"/>
              </svg>
            </div>
          </div>
          <div className="text-2xl font-extrabold text-ink-100 leading-none">{received.length}</div>
          <div className="text-xs text-ink-40 mt-1">Наборов получено</div>
        </div>

        {/* CO2 */}
        <div className="bg-surface rounded-card shadow-sm p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="w-9 h-9 rounded-[10px] bg-eco-soft flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-[18px] h-[18px] text-eco" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 12c0-5 4-9 9-9s9 4 9 9-4 9-9 9c-3 0-5-1-7-3M3 21v-6h6"/>
              </svg>
            </div>
          </div>
          <div className="text-2xl font-extrabold text-ink-100 leading-none">
            {co2}<span className="text-sm font-semibold text-ink-40 ml-1">кг CO₂</span>
          </div>
          <div className="text-xs text-ink-40 mt-1">Сэкономлено</div>
        </div>
      </div>

      {/* Panel */}
      <section className="bg-surface rounded-card shadow-sm p-5">
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="text-[11px] font-semibold text-ink-40 uppercase tracking-wider mb-0.5">История покупок</div>
            <h3 className="text-base font-bold text-ink-100">{orders.length} покупок за {MONTHS_RU[month - 1]} {year}</h3>
          </div>
          <div className="flex items-center gap-2 bg-line/60 rounded-[10px] px-3 py-2">
            <button onClick={prevMonth} className="text-ink-60 hover:text-ink-100 transition-colors">
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-sm font-semibold text-ink-100 min-w-[110px] text-center">{MONTHS_RU[month - 1]} {year}</span>
            <button onClick={nextMonth} className="text-ink-60 hover:text-ink-100 transition-colors">
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1,2,3].map(i => <div key={i} className="h-14 bg-line rounded-[10px] animate-pulse" />)}
          </div>
        ) : orders.length === 0 ? (
          <div className="flex flex-col items-center py-16 text-ink-40">
            <div className="text-4xl mb-3">🧾</div>
            <p className="font-medium">Нет покупок за этот период</p>
          </div>
        ) : (
          <div className="overflow-x-auto -mx-1">
            <table className="w-full min-w-[560px]">
              <thead>
                <tr className="border-b border-line">
                  <th className="text-left text-[11px] font-semibold text-ink-40 pb-2 px-1 uppercase tracking-wide">Дата</th>
                  <th className="text-left text-[11px] font-semibold text-ink-40 pb-2 px-1 uppercase tracking-wide">Набор</th>
                  <th className="text-right text-[11px] font-semibold text-ink-40 pb-2 px-1 uppercase tracking-wide">Сумма</th>
                  <th className="text-left text-[11px] font-semibold text-ink-40 pb-2 px-1 uppercase tracking-wide">Получено</th>
                  <th className="text-right text-[11px] font-semibold text-ink-40 pb-2 px-1 uppercase tracking-wide">Статус</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {orders.map(order => (
                  <tr key={order.id} className="hover:bg-bg/60 transition-colors">
                    <td className="py-3 px-1">
                      <span className="font-mono text-xs text-ink-100 font-semibold">
                        {new Date(order.created_at).toLocaleDateString("ru-RU", {
                          day: "2-digit", month: "2-digit", year: "numeric",
                          hour: "2-digit", minute: "2-digit",
                        })}
                      </span>
                    </td>
                    <td className="py-3 px-1">
                      <Link href={`/history/${order.id}`} className="text-sm font-semibold text-ink-100 hover:text-eco transition-colors truncate max-w-[160px] block">
                        {order.combo_title || `Заказ #${order.id.slice(-6)}`}
                      </Link>
                    </td>
                    <td className="py-3 px-1 text-right">
                      <span className="text-sm font-extrabold text-ink-100">{order.amount?.toLocaleString('ru-RU')} ₽</span>
                    </td>
                    <td className="py-3 px-1">
                      <span className="text-xs text-ink-40">
                        {order.completed_at ? new Date(order.completed_at).toLocaleDateString('ru-RU') : '—'}
                      </span>
                    </td>
                    <td className="py-3 px-1 text-right">
                      <span className={`text-[11px] px-2 py-1 rounded-full ${STATUS_PILL[order.status] || 'bg-line text-ink-40'}`}>
                        {ORDER_STATUS_LABELS[order.status] || order.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
