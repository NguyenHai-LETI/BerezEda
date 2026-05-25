"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Card } from "@/components/ui/card";

interface ConfirmCheckboxBlockProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label: string;
  warning?: string;
}

export function ConfirmCheckboxBlock({
  checked,
  onCheckedChange,
  label,
  warning,
}: ConfirmCheckboxBlockProps) {
  return (
    <Card className="p-4">
      {warning && (
        <div className="mb-4 p-3 bg-countdown/10 border border-countdown/20 rounded-md">
          <p className="text-sm font-medium text-countdown">{warning}</p>
        </div>
      )}
      <label className="flex items-start gap-3 cursor-pointer">
        <Checkbox
          checked={checked}
          onCheckedChange={onCheckedChange}
          className="mt-0.5"
        />
        <span className="text-sm text-text flex-1">{label}</span>
      </label>
    </Card>
  );
}
