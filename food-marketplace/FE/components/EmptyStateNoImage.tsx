import { ImageOff } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateNoImageProps {
  className?: string;
  size?: "sm" | "md" | "lg";
}

export function EmptyStateNoImage({ className, size = "md" }: EmptyStateNoImageProps) {
  const sizeClasses = {
    sm: "h-16 w-16",
    md: "h-24 w-24",
    lg: "h-32 w-32",
  };

  return (
    <div
      className={cn(
        "flex items-center justify-center bg-divider rounded-card",
        sizeClasses[size],
        className
      )}
      aria-label="No image available"
    >
      <ImageOff className="h-6 w-6 text-muted" aria-hidden="true" />
    </div>
  );
}
