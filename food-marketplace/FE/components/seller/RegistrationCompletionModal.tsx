"use client";

import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { QRCodeMockup } from "@/components/QRCodeMockup";
import { MapPin, Copy, Check } from "lucide-react";
import type { Locker, LockerUnit } from "@/lib/seller-mock";
import { cn } from "@/lib/utils";

interface RegistrationCompletionModalProps {
  open: boolean;
  onClose: () => void;
  onConfirmDeposit: () => void;
  locker: Locker;
  lockerUnit: LockerUnit;
  productCode: string;
  depositDeadlineSeconds?: number;
  salesDurationHours?: number;
}

export function RegistrationCompletionModal({
  open,
  onClose,
  onConfirmDeposit,
  locker,
  lockerUnit,
  productCode,
  depositDeadlineSeconds = 1200,
  salesDurationHours = 3,
}: RegistrationCompletionModalProps) {
  const [remainingSeconds, setRemainingSeconds] = useState(depositDeadlineSeconds);
  const [pinCopied, setPinCopied] = useState(false);
  
  // Generate a 6-digit PIN
  const unlockPin = "729764"; // In real app, this would come from backend

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

  const handleCopyPin = () => {
    navigator.clipboard.writeText(unlockPin);
    setPinCopied(true);
    setTimeout(() => setPinCopied(false), 2000);
  };

  // Generate QR code data (locker unlock code)
  const qrCodeData = `LOCKER-${locker.id}-${lockerUnit.id}-${unlockPin}`;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg w-[90vw] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-lg sm:text-xl mb-2 text-center">
            Product Registration Complete
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Countdown Timer */}
          <div className="text-center py-3 bg-countdown/10 rounded-card border border-countdown/20">
            <p className="text-xs sm:text-sm text-muted mb-1">Time remaining until deposit deadline</p>
            <p className="text-xl sm:text-2xl font-bold text-countdown">
              {formatTime(hours)}:{formatTime(minutes)}:{formatTime(secs)}
            </p>
          </div>

          {/* Sales Time Info */}
          <div className="space-y-3 p-3 bg-divider/30 rounded-card">
            <div>
              <p className="text-xs text-muted mb-1">Sales Start Time</p>
              <p className="text-xs text-text leading-relaxed">
                Sales will start from the moment the item is placed in the reserved box and the door is closed
              </p>
            </div>
            <div>
              <p className="text-xs text-muted mb-1">Sales End Time</p>
              <p className="text-xs text-text">
                {salesDurationHours} hours from sales start time
              </p>
            </div>
            <div>
              <p className="text-xs text-muted mb-1">Product Code</p>
              <p className="text-sm font-mono font-medium text-text">{productCode}</p>
            </div>
          </div>

          {/* Locker Information Card */}
          <Card className="p-4 sm:p-6">
            <h3 className="text-base sm:text-lg font-semibold mb-4">Sales Locker</h3>
            
            <div className="space-y-4">
              {/* Locker Name */}
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-muted" aria-hidden="true" />
                <div>
                  <p className="text-xs text-muted">Locker Name</p>
                  <p className="text-sm sm:text-base font-medium text-text">{locker.name}</p>
                </div>
              </div>

              {/* Box Number */}
              <div>
                <p className="text-xs text-muted mb-1">Box No.</p>
                <p className="text-lg sm:text-xl font-bold text-text">{lockerUnit.boxNo}</p>
              </div>

              {/* Unlock PIN */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-muted">Locker Unlock PIN</p>
                  <button
                    onClick={handleCopyPin}
                    className="flex items-center gap-1 text-xs text-primary hover:underline focus-ring"
                  >
                    {pinCopied ? (
                      <>
                        <Check className="h-3 w-3" aria-hidden="true" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-3 w-3" aria-hidden="true" />
                        Copy
                      </>
                    )}
                  </button>
                </div>
                <div className="p-3 bg-divider/50 rounded-md">
                  <p className="text-xl sm:text-2xl font-bold text-center font-mono text-text">
                    {unlockPin}
                  </p>
                </div>
              </div>

              {/* QR Code */}
              <div className="flex flex-col items-center pt-4 border-t border-divider">
                <p className="text-xs sm:text-sm text-muted mb-3">Locker Unlock QR Code</p>
                <QRCodeMockup code={qrCodeData} size="lg" />
                <p className="text-xs text-muted mt-3 text-center">
                  Locker Unlock Valid Until: {new Date(Date.now() + remainingSeconds * 1000).toLocaleString("en-US", {
                    year: "numeric",
                    month: "2-digit",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>
            </div>
          </Card>

          {/* Confirm Deposit Button */}
          <Button
            onClick={() => {
              onConfirmDeposit();
            }}
            className="w-full"
            size="lg"
          >
            Item has been placed
          </Button>
          <Button
            variant="ghost"
            onClick={onClose}
            className="w-full mt-2"
          >
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
