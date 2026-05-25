import { cn } from "@/lib/utils";
import { formatRUB } from "@/lib/format";

interface PriceDisplayProps {
  originalPrice: number;
  salePrice: number;
  className?: string;
}

export function PriceDisplay({ originalPrice, salePrice, className }: PriceDisplayProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className="text-lg font-bold text-text">{formatRUB(salePrice)}</span>
      {originalPrice > salePrice && (
        <span className="text-sm text-muted line-through">
          {formatRUB(originalPrice)}
        </span>
      )}
    </div>
  );
}
