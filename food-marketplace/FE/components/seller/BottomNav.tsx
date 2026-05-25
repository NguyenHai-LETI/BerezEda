"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, ShoppingBag, Plus, History, Settings, Bell } from "lucide-react";
import { sellerRoutes } from "@/lib/seller-routes";
import { cn } from "@/lib/utils";

const navItems = [
  { icon: Home, label: "Home", href: sellerRoutes.home },
  { icon: ShoppingBag, label: "Products", href: sellerRoutes.productManagement },
  { icon: Plus, label: "Add", href: sellerRoutes.addItem },
  { icon: History, label: "Sales", href: sellerRoutes.salesHistory },
  { icon: Bell, label: "Notifications", href: sellerRoutes.notifications },
] as const;

export function SellerBottomNav() {
  const pathname = usePathname();

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 bg-surface border-t border-divider lg:hidden safe-area-inset-bottom"
      aria-label="Bottom navigation"
    >
      <div className="flex items-center justify-around h-14 sm:h-16 px-1 sm:px-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center justify-center flex-1 h-full transition-colors focus-ring rounded-md py-1",
                isActive ? "text-primary" : "text-muted"
              )}
              aria-label={item.label}
            >
              <Icon className="h-4 w-4 sm:h-5 sm:w-5 mb-0.5 sm:mb-1" aria-hidden="true" />
              <span className="text-[10px] sm:text-xs leading-tight">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
