import type { ReactNode } from "react";
import { LockerSimShell } from "@/components/locker-sim/LockerSimShell";

export default function LockerSimLayout({ children }: { children: ReactNode }) {
  return <LockerSimShell>{children}</LockerSimShell>;
}

