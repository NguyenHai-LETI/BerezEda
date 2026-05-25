"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { CountdownDisplay } from "@/components/CountdownBadge";
import type { Locker, LockerUnit } from "@/lib/seller-mock";
import { cn } from "@/lib/utils";

interface RegistrationConfirmationPageProps {
  locker: Locker;
  lockerUnit: LockerUnit;
  depositDeadlineSeconds: number;
  onConfirm: () => void;
  onCancel: () => void;
}

export function RegistrationConfirmationPage({
  locker,
  lockerUnit,
  depositDeadlineSeconds,
  onConfirm,
  onCancel,
}: RegistrationConfirmationPageProps) {
  const [confirmed1, setConfirmed1] = useState(false);
  const [confirmed2, setConfirmed2] = useState(false);

  const canProceed = confirmed1 && confirmed2;

  return (
    <div className="min-h-screen p-3 sm:p-4 md:p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Countdown Timer */}
        <div className="text-center py-4 bg-countdown/10 rounded-card border border-countdown/20">
          <p className="text-xs sm:text-sm text-muted mb-2">Time remaining until deposit deadline</p>
          <CountdownDisplay seconds={depositDeadlineSeconds} className="text-2xl sm:text-3xl" />
        </div>

        {/* Instructions */}
        <div className="space-y-4">
          <div>
            <p className="text-sm sm:text-base text-text mb-3">
              Almost complete. Please check the following precautions and complete the registration.
            </p>
            <p className="text-sm text-text mb-4">
              Sales will start when you put the item in the locker and close the door. Please be sure to put the item in within the deposit time. Please note that if you are not in time, it will be automatically canceled.
            </p>
            <label className="flex items-start gap-3 cursor-pointer">
              <Checkbox
                checked={confirmed1}
                onCheckedChange={setConfirmed1}
                className="mt-0.5"
              />
              <span className="text-sm text-text flex-1">I have confirmed</span>
            </label>
          </div>

          <div>
            <p className="text-sm text-text mb-4">
              When unlocking the locker, there may be items from the previous store remaining. In that case, please take responsibility for properly disposing of the remaining items and then put in your own item.
            </p>
            <label className="flex items-start gap-3 cursor-pointer">
              <Checkbox
                checked={confirmed2}
                onCheckedChange={setConfirmed2}
                className="mt-0.5"
              />
              <span className="text-sm text-text flex-1">I have confirmed</span>
            </label>
          </div>

          {(!confirmed1 || !confirmed2) && (
            <div className="p-3 bg-countdown/10 border border-countdown/20 rounded-card">
              <p className="text-xs sm:text-sm text-countdown font-medium text-center">
                Please be sure to confirm and check the above contents
              </p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="sticky bottom-0 pb-4 pt-4 bg-surface border-t border-divider -mx-3 sm:-mx-4 md:-mx-6 px-3 sm:px-4 md:px-6">
          <Button
            onClick={onConfirm}
            disabled={!canProceed}
            className="w-full"
            size="lg"
          >
            I have confirmed the above matters
          </Button>
          <Button
            variant="ghost"
            onClick={onCancel}
            className="w-full mt-2"
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
