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

interface ItemCardVerticalProps {
  item: Item;
  shop: Shop;
  locker: Locker;
}

export function ItemCardVertical({ item, shop, locker }: ItemCardVerticalProps) {
  return (
    <Link href={routes.itemDetail(item.id)} className="block focus-ring h-full">
      <Card className="overflow-hidden hover:shadow-md transition-shadow h-full flex flex-col">
        <div className="p-3 sm:p-4 flex flex-col flex-1">
          <div className="mb-2 sm:mb-3">
            {item.images[0] ? (
              <div className="relative h-40 sm:h-48 md:h-52 w-full rounded-md overflow-hidden bg-divider">
                <Image
                  src={item.images[0]}
                  alt={item.title}
                  fill
                  className="object-cover"
                  sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                />
              </div>
            ) : (
              <EmptyStateNoImage size="lg" className="h-40 sm:h-48 md:h-52 w-full" />
            )}
          </div>
          <div className="flex items-start justify-between gap-2 mb-1.5 sm:mb-2">
            <h3 className="font-medium text-text text-sm sm:text-base line-clamp-2 flex-1">{item.title}</h3>
            <CountdownBadge seconds={item.countdownSeconds} className="flex-shrink-0" />
          </div>
          <p className="text-xs sm:text-sm text-muted mb-1.5 sm:mb-2 truncate">{shop.name}</p>
          <div className="flex items-center justify-between gap-2 mt-auto">
            <div className="min-w-0 flex-1">
              <p className="text-xs text-muted truncate">{locker.name}</p>
              <p className="text-xs text-muted">{formatDistance(locker.distanceKm)}</p>
            </div>
            <PriceDisplay
              originalPrice={item.originalPriceRUB}
              salePrice={item.salePriceRUB}
              className="text-sm sm:text-base flex-shrink-0"
            />
          </div>
        </div>
      </Card>
    </Link>
  );
}
