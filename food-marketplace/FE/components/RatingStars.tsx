import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

interface RatingStarsProps {
  rating: number;
  reviewsCount: number;
  className?: string;
}

export function RatingStars({ rating, reviewsCount, className }: RatingStarsProps) {
  const fullStars = Math.floor(rating);
  const hasHalfStar = rating % 1 >= 0.5;

  return (
    <div className={cn("flex items-center gap-1", className)}>
      <div className="flex items-center" aria-label={`Rating: ${rating} out of 5`}>
        {Array.from({ length: 5 }).map((_, i) => (
          <Star
            key={i}
            className={cn(
              "h-4 w-4",
              i < fullStars
                ? "fill-primary text-primary"
                : i === fullStars && hasHalfStar
                ? "fill-primary/50 text-primary"
                : "fill-none text-divider"
            )}
            aria-hidden="true"
          />
        ))}
      </div>
      <span className="text-sm text-muted ml-1">
        {rating} ({reviewsCount})
      </span>
    </div>
  );
}
