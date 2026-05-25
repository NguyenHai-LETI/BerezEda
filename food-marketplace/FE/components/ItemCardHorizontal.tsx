"use client";

import Link from "next/link";
import Image from "next/image";
import { routes } from "@/lib/routes";
import { formatDistance } from "@/lib/format";
import { CountdownBadge } from "@/components/CountdownBadge";
import { PriceDisplay } from "@/components/PriceDisplay";
import { EmptyStateNoImage } from "@/components/EmptyStateNoImage";
import { Card } from "@/components/ui/card";
import type { Item, Shop, Locker } from "@/lib/mock";

interface ItemCardHorizontalProps {
  item: Item;
  shop: Shop;
  locker: Locker;
}

export function ItemCardHorizontal({ item, shop, locker }: ItemCardHorizontalProps) {
  return (
    <Link href={routes.itemDetail(item.id)} className="block focus-ring">
      <Card className="overflow-hidden hover:shadow-md transition-shadow h-full">
        <div className="flex gap-3 sm:gap-4 p-3 sm:p-4">
          <div className="flex-shrink-0">
            {item.images[0] ? (
              <div className="relative h-20 w-20 sm:h-24 sm:w-24 rounded-md overflow-hidden bg-divider">
                <Image
                  src={item.images[0]}
                  alt={item.title}
                  fill
                  className="object-cover"
                  sizes="(max-width: 640px) 80px, 96px"
                />
              </div>
            ) : (
              <EmptyStateNoImage size="sm" className="h-20 w-20 sm:h-24 sm:w-24" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2 mb-1.5 sm:mb-2">
              <h3 className="font-medium text-text text-sm sm:text-base line-clamp-2 flex-1">{item.title}</h3>
              <CountdownBadge seconds={item.countdownSeconds} className="flex-shrink-0" />
            </div>
            <p className="text-xs sm:text-sm text-muted mb-1.5 sm:mb-2 truncate">{shop.name}</p>
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="min-w-0 flex-1">
                <p className="text-xs text-muted mb-0.5 truncate">{locker.name}</p>
                <p className="text-xs text-muted">{formatDistance(locker.distanceKm)}</p>
              </div>
              <div className="flex-shrink-0">
                <PriceDisplay
                  originalPrice={item.originalPriceRUB}
                  salePrice={item.salePriceRUB}
                  className="text-sm sm:text-base"
                />
              </div>
            </div>
          </div>
        </div>
      </Card>
    </Link>
  );
}
