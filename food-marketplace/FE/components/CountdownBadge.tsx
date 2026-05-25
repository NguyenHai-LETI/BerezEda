"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface CountdownBadgeProps {
  seconds: number;
  className?: string;
}

export function CountdownBadge({ seconds: initialSeconds, className }: CountdownBadgeProps) {
  const [seconds, setSeconds] = useState(initialSeconds);

  useEffect(() => {
    if (seconds <= 0) return;

    const interval = setInterval(() => {
      setSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [seconds]);

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const formatTime = (value: number): string => {
    return value.toString().padStart(2, "0");
  };

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-1 rounded text-sm font-medium bg-countdown/10 text-countdown",
        className
      )}
      aria-live="polite"
      aria-label={`Time remaining: ${hours} hours ${minutes} minutes ${secs} seconds`}
    >
      {hours > 0 && `${formatTime(hours)}:`}
      {formatTime(minutes)}:{formatTime(secs)}
    </span>
  );
}

// Larger countdown display for confirmation pages
export function CountdownDisplay({ seconds: initialSeconds, className }: CountdownBadgeProps) {
  const [seconds, setSeconds] = useState(initialSeconds);

  useEffect(() => {
    if (seconds <= 0) return;

    const interval = setInterval(() => {
      setSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [seconds]);

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const formatTime = (value: number): string => {
    return value.toString().padStart(2, "0");
  };

  return (
    <span
      className={cn(
        "inline-block font-bold text-countdown",
        className
      )}
      aria-live="polite"
    >
      {formatTime(hours)}:{formatTime(minutes)}:{formatTime(secs)}
    </span>
  );
}
