"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { updateLockerUnitStatus } from "@/lib/firebase-placeholder";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import cameraPreview from "@/WIN_20260201_15_11_44_Pro.jpg";

function parseQr(qr: string): { lockerId: string; unitId: string } | null {
  // Expected: LOCKER-<lockerId>-<unitId>-<pin>
  const parts = qr.trim().split("-");
  if (parts.length < 4) return null;
  if (parts[0] !== "LOCKER") return null;
  return { lockerId: parts[1], unitId: parts[2] };
}

export function ScanPane() {
  const router = useRouter();
  const [qr, setQr] = useState("");
  const parsed = useMemo(() => parseQr(qr), [qr]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const last = sessionStorage.getItem("lockerSim.lastQr");
    if (last) setQr(last);
  }, []);

  const complete = async () => {
    const p = parseQr(qr);
    if (!p) {
      setError("Invalid QR format. Paste: LOCKER-lockerId-unitId-pin");
      return;
    }
    setError(null);
    sessionStorage.setItem("lockerSim.lastQr", qr);
    sessionStorage.setItem("lockerSim.lockerId", p.lockerId);
    sessionStorage.setItem("lockerSim.unitId", p.unitId);

    // Mark as placing (red) in realtime
    await updateLockerUnitStatus(p.lockerId, p.unitId, "placing");
    router.push("/locker-sim/deposit");
  };

  return (
    <div className="h-full p-6">
      <h1 className="text-xl font-semibold mb-4">Scan QR</h1>

      <Card className="p-4 mb-4">
        <div className="text-sm text-muted mb-2">Camera (simulation)</div>
        <div className="relative h-56 bg-divider rounded-md overflow-hidden">
          <Image
            src={cameraPreview}
            alt="Camera preview"
            fill
            className="object-contain"
            priority
          />
        </div>
        <div className="text-xs text-muted mt-2">
          For simulation, paste QR text below then press “Complete scan”.
        </div>
      </Card>

      <div className="space-y-2">
        <label className="text-sm font-medium text-text">QR text</label>
        <input
          value={qr}
          onChange={(e) => setQr(e.target.value)}
          className="w-full px-3 py-2 border border-divider rounded-md focus-ring text-sm"
          placeholder="LOCKER-locker1-unit1-2-729764"
        />
        {error && <div className="text-xs text-danger">{error}</div>}
        <Button className="w-full" onClick={complete} disabled={!parsed}>
          Complete scan
        </Button>
      </div>
    </div>
  );
}

