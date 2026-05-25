"use client";

import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Bell, ShoppingCart, Package, CreditCard, Settings } from "lucide-react";
import { formatDateTime } from "@/lib/format";
import type { SellerNotification } from "@/lib/seller-mock";
import { cn } from "@/lib/utils";

interface NotificationListProps {
  notifications: SellerNotification[];
  onMarkAsRead?: (id: string) => void;
  className?: string;
}

const notificationIcons = {
  order: ShoppingCart,
  stock: Package,
  payment: CreditCard,
  system: Settings,
};

const notificationColors = {
  order: "text-blue-600",
  stock: "text-orange-600",
  payment: "text-green-600",
  system: "text-muted",
};

export function NotificationList({
  notifications,
  onMarkAsRead,
  className,
}: NotificationListProps) {
  if (notifications.length === 0) {
    return (
      <div className={cn("flex flex-col items-center justify-center py-12", className)}>
        <Bell className="h-12 w-12 text-muted mb-4" aria-hidden="true" />
        <p className="text-sm text-muted">No notifications</p>
      </div>
    );
  }

  return (
    <Card className={className}>
      <div className="divide-y divide-divider">
        {notifications.map((notification) => {
          const Icon = notificationIcons[notification.type];
          const iconColor = notificationColors[notification.type];

          return (
            <div
              key={notification.id}
              className={cn(
                "p-3 sm:p-4 hover:bg-divider/50 transition-colors cursor-pointer",
                !notification.readStatus && "bg-primary/5"
              )}
              onClick={() => onMarkAsRead?.(notification.id)}
            >
              <div className="flex items-start gap-3">
                <div className={cn("flex-shrink-0 mt-0.5", iconColor)}>
                  <Icon className="h-4 w-4 sm:h-5 sm:w-5" aria-hidden="true" />
                </div>
                <div className="flex-1 min-w-0">
                  <p
                    className={cn(
                      "text-sm sm:text-base mb-1",
                      !notification.readStatus && "font-medium text-text",
                      notification.readStatus && "text-muted"
                    )}
                  >
                    {notification.message}
                  </p>
                  <p className="text-xs text-muted">
                    {formatDateTime(notification.dateTime)}
                  </p>
                </div>
                {!notification.readStatus && (
                  <div className="h-2 w-2 rounded-full bg-primary flex-shrink-0 mt-2" />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
