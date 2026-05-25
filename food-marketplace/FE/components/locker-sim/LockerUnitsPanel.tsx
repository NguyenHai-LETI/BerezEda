"use client";

import { useEffect, useMemo, useState } from "react";
import { lockers } from "@/lib/mock";
import { subscribeToLockerUnits } from "@/lib/firebase-placeholder";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type SimStatus = "available" | "booked" | "placing";

function mapStatus(s: string): SimStatus {
  if (s === "placing") return "placing";
  if (s === "available") return "available";
  return "booked";
}

export function LockerUnitsPanel() {
  const [lockerId, setLockerId] = useState<string>(lockers[0]?.id ?? "locker1");
  const [units, setUnits] = useState<
    { id: string; temperature: number; status: SimStatus }[]
  >([]);

  useEffect(() => {
    const unsub = subscribeToLockerUnits(lockerId, (next) => {
      setUnits(
        next.map((u) => ({
          id: u.id,
          temperature: u.temperature,
          status: mapStatus(u.status),
        }))
      );
    });
    return () => unsub();
  }, [lockerId]);

  const locker = useMemo(() => {
    return lockers.find((l) => l.id === lockerId);
  }, [lockerId]);

  const unitCardClass = (status: SimStatus) => {
    switch (status) {
      case "available":
        return "bg-blue-300 hover:bg-blue-400";
      case "placing":
        return "bg-red-400";
      case "booked":
      default:
        return "bg-gray-300";
    }
  };

  return (
    <div className="p-4 space-y-4">
      {/* Locker selector dropdown */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-text">Выберите постамат</label>
        <select
          value={lockerId}
          onChange={(e) => setLockerId(e.target.value)}
          className="w-full px-3 py-2 border border-divider rounded-md focus-ring text-sm bg-background"
        >
          {lockers.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name} — {l.areaDescription}
            </option>
          ))}
        </select>
      </div>

      {/* Locker info */}
      {locker && (
        <div className="bg-background rounded-lg p-3 border border-divider">
          <div className="text-base font-semibold text-text">{locker.name}</div>
          <div className="text-xs text-muted mt-1">{locker.areaDescription} · Box {locker.boxNo}</div>
        </div>
      )}

      {/* Legend */}
      <div className="flex gap-4 text-xs text-muted">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-blue-300 inline-block" /> Свободно
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-red-400 inline-block" /> Размещение
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-gray-300 inline-block" /> Занято
        </span>
      </div>

      {/* Units grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {units.map((u, idx) => (
          <Card
            key={u.id}
            className={cn(
              "p-3 sm:p-4 min-h-[96px] flex flex-col justify-between",
              unitCardClass(u.status)
            )}
          >
            <div className="flex items-center justify-between">
              <div className="text-sm sm:text-base font-semibold text-text">
                {idx + 1} ({u.temperature}°C)
              </div>
            </div>
            <div className="text-xs text-text/80">
              {u.status === "available"
                ? "Свободно"
                : u.status === "placing"
                  ? "Размещение"
                  : "Занято"}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
