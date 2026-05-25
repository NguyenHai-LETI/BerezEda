"use client";

import { useEffect, useState } from "react";
import { MapPin } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { LockerUnit } from "@/lib/seller-mock";
import { subscribeToLockerUnits } from "@/lib/firebase-placeholder";
import { cn } from "@/lib/utils";

interface LockerUnitSelectorProps {
  lockerId: string;
  lockerName: string;
  units: LockerUnit[];
  selectedUnitId?: string;
  onSelectUnit: (unitId: string) => void;
  className?: string;
}

export function LockerUnitSelector({
  lockerId,
  lockerName,
  units: initialUnits,
  selectedUnitId,
  onSelectUnit,
  className,
}: LockerUnitSelectorProps) {
  const [units, setUnits] = useState(initialUnits);

  // Subscribe to real-time updates from Firebase
  useEffect(() => {
    // In production, this would use Firebase real-time database
    const unsubscribe = subscribeToLockerUnits(lockerId, (updatedUnits) => {
      // Update units with real-time data
      // This is a placeholder - in real app, merge updatedUnits with current units
      setUnits((prev) => {
        // Merge logic would go here
        return prev;
      });
    });

    return () => {
      unsubscribe();
    };
  }, [lockerId]);

  const getUnitCardStyle = (unit: LockerUnit, isSelected: boolean) => {
    if (isSelected) {
      return "ring-2 ring-primary bg-primary/10";
    }
    
    switch (unit.status) {
      case "available":
        return "bg-blue-300 hover:bg-blue-400 cursor-pointer";
      case "occupied":
        return "bg-gray-200 cursor-not-allowed opacity-60";
      case "in_use_by_other":
        return "bg-red-50 hover:bg-red-100 cursor-not-allowed opacity-60";
      default:
        return "bg-gray-100 cursor-not-allowed opacity-60";
    }
  };

  const getStatusLabel = (unit: LockerUnit) => {
    switch (unit.status) {
      case "available":
        return { text: "Available", className: "bg-green-100 text-green-700" };
      case "occupied":
        return { text: "In Use", className: "bg-gray-300 text-gray-700" };
      case "in_use_by_other":
        return { text: "Reserved", className: "bg-red-200 text-red-700" };
      default:
        return { text: "Unavailable", className: "bg-gray-300 text-gray-700" };
    }
  };

  const isUnitSelectable = (unit: LockerUnit) => {
    return unit.status === "available";
  };

  return (
    <div className={cn("space-y-4", className)}>
      {/* Locker Station Selection */}
      <div className="p-3 sm:p-4 bg-divider/30 rounded-card">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm sm:text-base font-medium text-text">Available Lockers</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 px-3 py-2 bg-surface border border-divider rounded-md flex items-center justify-between">
            <span className="text-sm sm:text-base text-text">{lockerName}</span>
            <span className="text-muted text-xs">▼</span>
          </div>
          <button className="p-2 border border-divider rounded-md hover:bg-divider focus-ring">
            <MapPin className="h-4 w-4 text-muted" aria-label="View location" />
          </button>
        </div>
      </div>

      {/* Locker Units Grid */}
      {units.length === 0 ? (
        <div className="text-center py-8 text-muted">
          <p className="text-sm">No available locker units</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
          {units.map((unit) => {
            const isSelected = selectedUnitId === unit.id;
            const isSelectable = isUnitSelectable(unit);
            const statusLabel = getStatusLabel(unit);

            return (
              <Card
                key={unit.id}
                className={cn(
                  "p-3 sm:p-4 md:p-5 transition-all hover:shadow-md min-h-[96px] sm:min-h-[112px] flex flex-col",
                  getUnitCardStyle(unit, isSelected)
                )}
                onClick={() => {
                  if (isSelectable) {
                    onSelectUnit(unit.id);
                  }
                }}
              >
                <div className="flex flex-col space-y-2 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm sm:text-base font-semibold text-text">
                      {unit.unitNumber} ({unit.temperature}°C)
                    </span>
                    <span className={cn(
                      "text-xs px-1.5 py-0.5 rounded-full whitespace-nowrap",
                      statusLabel.className
                    )}>
                      {statusLabel.text}
                    </span>
                  </div>
                  {!isSelectable && (
                    <div className="w-full text-xs sm:text-sm text-center py-1.5 px-2 bg-divider/50 rounded text-muted mt-auto">
                      {unit.status === "occupied" ? "In Use" : "Reserved"}
                    </div>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
