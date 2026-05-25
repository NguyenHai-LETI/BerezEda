"use client";

import { Trash2 } from "lucide-react";
import { RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import type { PaymentCard } from "@/lib/mock";

interface PaymentCardRowProps {
  card: PaymentCard;
  selected: boolean;
  onSetDefault: (cardId: string, isDefault: boolean) => void;
  onDelete: (cardId: string) => void;
}

export function PaymentCardRow({
  card,
  selected,
  onSetDefault,
  onDelete,
}: PaymentCardRowProps) {
  return (
    <div>
      <div className="flex items-center gap-4 p-4">
        <RadioGroupItem
          value={card.id}
          aria-label={`Select ${card.brand} card ending in ${card.last4}`}
        />
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium">{card.brand}</span>
            <span className="text-muted">****{card.last4}</span>
            {card.isDefault && (
              <span className="text-xs text-muted bg-divider px-2 py-0.5 rounded">
                Default
              </span>
            )}
          </div>
          <p className="text-sm text-muted">Expires {card.expiry}</p>
        </div>
        <div className="flex items-center gap-2">
          {!card.isDefault && (
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <Checkbox
                checked={false}
                onCheckedChange={(checked) => onSetDefault(card.id, checked as boolean)}
              />
              <span className="text-muted">Set as default</span>
            </label>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(card.id)}
            aria-label={`Delete ${card.brand} card ending in ${card.last4}`}
          >
            <Trash2 className="h-4 w-4 text-danger" aria-hidden="true" />
          </Button>
        </div>
      </div>
      <Separator />
    </div>
  );
}
