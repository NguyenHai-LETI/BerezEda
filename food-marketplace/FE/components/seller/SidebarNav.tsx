"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, ShoppingBag, Plus, History, Settings, Bell } from "lucide-react";
import { sellerRoutes } from "@/lib/seller-routes";
import { cn } from "@/lib/utils";

const navItems = [
  { icon: Home, label: "Dashboard", href: sellerRoutes.home },
  { icon: ShoppingBag, label: "Product Management", href: sellerRoutes.productManagement },
  { icon: Plus, label: "Add New Item", href: sellerRoutes.addItem },
  { icon: History, label: "Sales History", href: sellerRoutes.salesHistory },
  { icon: Bell, label: "Notifications", href: sellerRoutes.notifications },
  { icon: Settings, label: "Profile Settings", href: sellerRoutes.profileSettings },
] as const;

export function SellerSidebarNav() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:flex lg:flex-col lg:w-64 lg:border-r lg:border-divider lg:bg-surface">
      <nav className="flex-1 p-4" aria-label="Sidebar navigation">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-4 py-3 rounded-md transition-colors focus-ring",
                    isActive
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-text hover:bg-divider"
                  )}
                >
                  <Icon className="h-5 w-5" aria-hidden="true" />
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
