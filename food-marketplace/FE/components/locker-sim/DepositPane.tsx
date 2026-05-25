"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { updateLockerUnitStatus } from "@/lib/firebase-placeholder";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function DepositPane() {
  const router = useRouter();
  const [lockerId, setLockerId] = useState<string | null>(null);
  const [unitId, setUnitId] = useState<string | null>(null);

  useEffect(() => {
    setLockerId(sessionStorage.getItem("lockerSim.lockerId"));
    setUnitId(sessionStorage.getItem("lockerSim.unitId"));
  }, []);

  const done = async () => {
    if (!lockerId || !unitId) {
      router.push("/locker-sim");
      return;
    }
    // Mark as booked (gray) after placing
    await updateLockerUnitStatus(lockerId, unitId, "occupied");
    router.push("/locker-sim");
  };

  return (
    <div className="h-full p-6">
      <h1 className="text-xl font-semibold mb-4">Deposit simulation</h1>
      <Card className="p-4 mb-4">
        <div className="text-sm text-text mb-1">Selected unit</div>
        <div className="text-xs text-muted">
          Locker: {lockerId ?? "-"} / Unit: {unitId ?? "-"}
        </div>
      </Card>

      <Button className="w-full" onClick={done}>
        Simulate putting item into locker
      </Button>
    </div>
  );
}

