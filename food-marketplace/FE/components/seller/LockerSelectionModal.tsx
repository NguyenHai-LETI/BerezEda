"use client";

import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { MapPin } from "lucide-react";
import type { Locker, LockerUnit } from "@/lib/seller-mock";
import { cn } from "@/lib/utils";

interface LockerSelectionModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  locker: Locker;
  lockerUnit: LockerUnit;
  depositDeadlineSeconds?: number; // Time in seconds until deposit deadline
}

export function LockerSelectionModal({
  open,
  onClose,
  onConfirm,
  locker,
  lockerUnit,
  depositDeadlineSeconds = 1200, // 20 minutes default
}: LockerSelectionModalProps) {
  const [remainingSeconds, setRemainingSeconds] = useState(depositDeadlineSeconds);

  useEffect(() => {
    if (!open || remainingSeconds <= 0) return;

    const interval = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [open, remainingSeconds]);

  const hours = Math.floor(remainingSeconds / 3600);
  const minutes = Math.floor((remainingSeconds % 3600) / 60);
  const secs = remainingSeconds % 60;

  const formatTime = (value: number): string => {
    return value.toString().padStart(2, "0");
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md w-[90vw]">
        <DialogHeader>
          <DialogTitle className="text-lg sm:text-xl mb-4 text-center">
            Please confirm the selected content
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Countdown Timer */}
          <div className="text-center py-4 bg-countdown/10 rounded-card border border-countdown/20">
            <p className="text-xs sm:text-sm text-muted mb-2">Time remaining until deposit deadline</p>
            <p className="text-2xl sm:text-3xl font-bold text-countdown">
              {formatTime(hours)}:{formatTime(minutes)}:{formatTime(secs)}
            </p>
          </div>

          {/* Locker Information */}
          <div className="space-y-3 p-4 bg-divider/30 rounded-card">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-muted" aria-hidden="true" />
              <div>
                <p className="text-xs text-muted">Locker Name</p>
                <p className="text-sm sm:text-base font-medium text-text">{locker.name}</p>
              </div>
            </div>
            <div>
              <p className="text-xs text-muted">Box No.</p>
              <p className="text-lg sm:text-xl font-bold text-text">{lockerUnit.boxNo}</p>
            </div>
          </div>

          {/* Instruction */}
          <div className="p-3 bg-primary/5 rounded-card">
            <p className="text-xs sm:text-sm text-text text-center">
              Please put the item into the locker within 20 minutes
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={onClose}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={onConfirm}
              className="flex-1"
            >
              Confirm
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
