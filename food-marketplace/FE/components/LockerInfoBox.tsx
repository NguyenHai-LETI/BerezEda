import { MapPin } from "lucide-react";
import { formatDistance } from "@/lib/format";
import type { Locker } from "@/lib/mock";
import { Card } from "@/components/ui/card";

interface LockerInfoBoxProps {
  locker: Locker;
  className?: string;
}

export function LockerInfoBox({ locker, className }: LockerInfoBoxProps) {
  return (
    <Card className={className}>
      <div className="p-4">
        <div className="flex items-start gap-3">
          <MapPin className="h-5 w-5 text-muted mt-0.5 flex-shrink-0" aria-hidden="true" />
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-text mb-1">{locker.name}</h3>
            <p className="text-sm text-muted mb-2">{locker.areaDescription}</p>
            <div className="flex items-center gap-4 text-sm">
              <span className="text-muted">Box No.</span>
              <span className="font-medium text-text">{locker.boxNo}</span>
              <span className="text-muted ml-auto">{formatDistance(locker.distanceKm)}</span>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
