"use client";

import { cn } from "@/lib/utils";

interface QRCodeMockupProps {
  code?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function QRCodeMockup({ 
  code = "LOCKER-ABC123-XYZ789", 
  size = "md",
  className 
}: QRCodeMockupProps) {
  const sizeClasses = {
    sm: "w-32 h-32",
    md: "w-48 h-48",
    lg: "w-64 h-64",
  };

  // Generate a more realistic QR code pattern
  return (
    <div className={cn("flex flex-col items-center", className)}>
      <div
        className={cn(
          "relative bg-white border-2 border-text rounded-lg p-3 sm:p-4 shadow-lg",
          sizeClasses[size]
        )}
        aria-label="QR Code for locker access"
      >
        {/* Mock QR Code Pattern - more detailed */}
        <div className="w-full h-full grid grid-cols-12 gap-0.5">
          {Array.from({ length: 144 }).map((_, i) => {
            const row = Math.floor(i / 12);
            const col = i % 12;
            
            // Corner squares (position markers)
            const isCornerSquare = 
              ((row < 7 && col < 7) && (row < 2 || row > 4 || col < 2 || col > 4)) ||
              ((row < 7 && col >= 5) && (row < 2 || row > 4 || col < 7 || col > 9)) ||
              ((row >= 5 && col < 7) && (row < 7 || row > 9 || col < 2 || col > 4));
            
            // Timing patterns
            const isTimingPattern = (row === 6 && col >= 2 && col <= 9) || (col === 6 && row >= 2 && row <= 9);
            
            // Data pattern (more random-like)
            const hash = (code.charCodeAt(i % code.length) + row * 12 + col) % 3;
            const isDataPattern = hash === 0 || (row + col) % 4 === 0;
            
            const isBlack = isCornerSquare || isTimingPattern || isDataPattern;
            
            return (
              <div
                key={i}
                className={cn(
                  "aspect-square",
                  isBlack ? "bg-text" : "bg-white"
                )}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
