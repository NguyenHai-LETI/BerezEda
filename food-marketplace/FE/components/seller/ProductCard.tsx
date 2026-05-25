"use client";

import Link from "next/link";
import Image from "next/image";
import { Edit, Trash2, Package } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyStateNoImage } from "@/components/EmptyStateNoImage";
import { formatRUB } from "@/lib/format";
import type { SellerItem } from "@/lib/seller-mock";
import { sellerRoutes } from "@/lib/seller-routes";
import { cn } from "@/lib/utils";

interface ProductCardProps {
  item: SellerItem;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
}

export function ProductCard({ item, onEdit, onDelete }: ProductCardProps) {
  const statusColors = {
    active: "bg-green-100 text-green-700",
    inactive: "bg-gray-100 text-gray-700",
    pending: "bg-yellow-100 text-yellow-700",
    sold_out: "bg-red-100 text-red-700",
  };

  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow">
      <div className="p-3 sm:p-4">
        <div className="flex gap-3 sm:gap-4">
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
            <div className="flex items-start justify-between gap-2 mb-1.5">
              <Link
                href={sellerRoutes.itemDetail(item.id)}
                className="flex-1 min-w-0 focus-ring"
              >
                <h3 className="font-medium text-text text-sm sm:text-base line-clamp-2 hover:text-primary transition-colors">
                  {item.title}
                </h3>
              </Link>
              <span
                className={cn(
                  "text-xs px-2 py-0.5 rounded-full whitespace-nowrap flex-shrink-0",
                  statusColors[item.status]
                )}
              >
                {item.status.replace("_", " ")}
              </span>
            </div>
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className="text-sm sm:text-base font-semibold text-text">
                {formatRUB(item.price)}
              </span>
              <div className="flex items-center gap-1 text-xs text-muted">
                <Package className="h-3 w-3" aria-hidden="true" />
                <span>Stock: {item.stockQuantity}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onEdit?.(item.id)}
                className="h-8 px-2 sm:px-3 text-xs"
                aria-label={`Edit ${item.title}`}
              >
                <Edit className="h-3 w-3 sm:h-4 sm:w-4 mr-1" aria-hidden="true" />
                Edit
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDelete?.(item.id)}
                className="h-8 px-2 sm:px-3 text-xs text-danger hover:text-danger hover:bg-danger/10"
                aria-label={`Delete ${item.title}`}
              >
                <Trash2 className="h-3 w-3 sm:h-4 sm:w-4 mr-1" aria-hidden="true" />
                Delete
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
