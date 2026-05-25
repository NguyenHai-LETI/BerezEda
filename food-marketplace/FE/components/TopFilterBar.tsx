"use client";

import { useState } from "react";
import Link from "next/link";
import { MapPin, ChevronDown } from "lucide-react";
import { routes } from "@/lib/routes";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function TopFilterBar() {
  const [sortBy, setSortBy] = useState<"nearest" | "available">("nearest");
  const [showFilter, setShowFilter] = useState(false);

  return (
    <div className="flex items-center gap-2 p-3 sm:p-4 bg-surface border-b border-divider sticky top-0 z-20">
      <button
        onClick={() => setSortBy(sortBy === "nearest" ? "available" : "nearest")}
        className="px-3 sm:px-4 py-2 text-xs sm:text-sm rounded-md border border-divider hover:bg-divider focus-ring transition-colors whitespace-nowrap"
        aria-label={`Sort by ${sortBy === "nearest" ? "available" : "nearest"}`}
      >
        {sortBy === "nearest" ? "Nearest" : "Available"}
      </button>

      <div className="relative flex-1 min-w-0">
        <button
          onClick={() => setShowFilter(!showFilter)}
          className="w-full px-3 sm:px-4 py-2 text-xs sm:text-sm rounded-md border border-divider hover:bg-divider focus-ring transition-colors flex items-center justify-between"
          aria-expanded={showFilter}
          aria-label="Filter options"
        >
          <span className="truncate">Available now</span>
          <ChevronDown
            className={cn(
              "h-3 w-3 sm:h-4 sm:w-4 transition-transform flex-shrink-0 ml-2",
              showFilter && "rotate-180"
            )}
            aria-hidden="true"
          />
        </button>
        {showFilter && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-surface border border-divider rounded-md shadow-lg z-10">
            <button
              className="w-full px-4 py-2 text-left text-sm hover:bg-divider focus-ring"
              onClick={() => setShowFilter(false)}
            >
              Available now
            </button>
            <button
              className="w-full px-4 py-2 text-left text-sm hover:bg-divider focus-ring"
              onClick={() => setShowFilter(false)}
            >
              All items
            </button>
          </div>
        )}
      </div>

      <Link href={routes.map} className="flex-shrink-0">
        <Button
          variant="secondary"
          size="sm"
          className="gap-1 sm:gap-2 text-xs sm:text-sm px-2 sm:px-3"
          aria-label="Open map"
        >
          <MapPin className="h-3 w-3 sm:h-4 sm:w-4" aria-hidden="true" />
          <span className="hidden sm:inline">MAP</span>
        </Button>
      </Link>
    </div>
  );
}
