"use client";

import { Card } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Package, ShoppingCart } from "lucide-react";
import { formatRUB } from "@/lib/format";
import type { SalesSummary as SalesSummaryType } from "@/lib/seller-mock";
import { cn } from "@/lib/utils";

interface SalesSummaryProps {
  summary: SalesSummaryType;
  className?: string;
}

export function SalesSummary({ summary, className }: SalesSummaryProps) {
  const revenueChange =
    summary.lastMonthRevenue > 0
      ? ((summary.thisMonthRevenue - summary.lastMonthRevenue) / summary.lastMonthRevenue) * 100
      : 0;

  const stats = [
    {
      label: "Total Revenue",
      value: formatRUB(summary.totalRevenue),
      icon: TrendingUp,
      color: "text-primary",
    },
    {
      label: "Total Sales",
      value: summary.totalSales.toString(),
      icon: ShoppingCart,
      color: "text-blue-600",
    },
    {
      label: "Active Items",
      value: summary.activeItems.toString(),
      icon: Package,
      color: "text-green-600",
    },
    {
      label: "Pending Orders",
      value: summary.pendingOrders.toString(),
      icon: ShoppingCart,
      color: "text-orange-600",
    },
  ];

  return (
    <div className={cn("space-y-4", className)}>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label} className="p-3 sm:p-4">
              <div className="flex items-center justify-between mb-2">
                <Icon className={cn("h-4 w-4 sm:h-5 sm:w-5", stat.color)} aria-hidden="true" />
              </div>
              <p className="text-xs sm:text-sm text-muted mb-1">{stat.label}</p>
              <p className="text-lg sm:text-xl font-semibold text-text">{stat.value}</p>
            </Card>
          );
        })}
      </div>

      <Card className="p-3 sm:p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs sm:text-sm text-muted mb-1">This Month Revenue</p>
            <p className="text-xl sm:text-2xl font-semibold text-text">
              {formatRUB(summary.thisMonthRevenue)}
            </p>
          </div>
          {summary.lastMonthRevenue > 0 && (
            <div className="text-right">
              <div
                className={cn(
                  "flex items-center gap-1 text-sm font-medium",
                  revenueChange >= 0 ? "text-green-600" : "text-red-600"
                )}
              >
                {revenueChange >= 0 ? (
                  <TrendingUp className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <TrendingDown className="h-4 w-4" aria-hidden="true" />
                )}
                <span>{Math.abs(revenueChange).toFixed(1)}%</span>
              </div>
              <p className="text-xs text-muted">vs last month</p>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
