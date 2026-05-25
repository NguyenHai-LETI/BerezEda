"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { CheckCircle2 } from "lucide-react";
import { QRCodeMockup } from "@/components/QRCodeMockup";

interface SuccessModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  message?: string;
  qrCode?: string;
}

export function SuccessModal({
  open,
  onClose,
  title = "Purchase completed",
  message = "Your purchase has been completed successfully.",
  qrCode,
}: SuccessModalProps) {
  // Generate a random locker code if not provided
  const lockerCode = qrCode || `LOCKER-${Math.random().toString(36).substring(2, 8).toUpperCase()}-${Date.now().toString(36).substring(7, 11).toUpperCase()}`;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md w-[90vw] max-w-md">
        <DialogHeader>
          <div className="flex flex-col items-center text-center">
            <CheckCircle2 className="h-12 w-12 sm:h-16 sm:w-16 text-primary mb-4" aria-hidden="true" />
            <DialogTitle className="text-lg sm:text-xl mb-2">{title}</DialogTitle>
            {message && <p className="text-xs sm:text-sm text-muted mb-6 px-4">{message}</p>}
            
            {/* QR Code Section */}
            <div className="w-full flex flex-col items-center py-4 border-t border-divider">
              <h3 className="text-sm font-semibold mb-4 text-text">Locker Access Code</h3>
              <QRCodeMockup code={lockerCode} size="md" />
            </div>
          </div>
        </DialogHeader>
        <div className="flex justify-center mt-6 pb-2">
          <Button onClick={onClose} className="min-w-[120px] w-full sm:w-auto">
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
