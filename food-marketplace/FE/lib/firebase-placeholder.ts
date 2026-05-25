/**
 * Firebase Real-time Database Placeholder
 * 
 * This file contains placeholder functions for Firebase integration.
 * In production, replace these with actual Firebase SDK calls.
 * 
 * Example Firebase setup:
 * 
 * import { initializeApp } from 'firebase/app';
 * import { getDatabase, ref, onValue, off } from 'firebase/database';
 * 
 * const firebaseConfig = {
 *   // Your Firebase config
 * };
 * 
 * const app = initializeApp(firebaseConfig);
 * const database = getDatabase(app);
 */

export interface LockerUnitStatus {
  id: string;
  status: "available" | "occupied" | "reserved" | "maintenance" | "placing";
  temperature: number;
  lastUpdated: Date;
}

type LockerUnitStatusListener = (units: LockerUnitStatus[]) => void;

type LockerUnitsByLocker = Record<string, LockerUnitStatus[]>;

let initialized = false;
let unitsByLocker: LockerUnitsByLocker = {};
const listenersByLocker = new Map<string, Set<LockerUnitStatusListener>>();

function initIfNeeded() {
  if (initialized) return;
  initialized = true;

  // Lazy import to avoid circular deps issues at module load
  // @ts-ignore
  const sellerMock = require("./seller-mock") as typeof import("./seller-mock");

  // Seed with seller-mock lockerUnits
  const seed: LockerUnitsByLocker = {};
  for (const unit of sellerMock.lockerUnits) {
    const lockerId = unit.lockerId;
    const mappedStatus: LockerUnitStatus["status"] =
      unit.status === "available"
        ? "available"
        : unit.status === "occupied"
          ? "occupied"
          : "reserved";

    seed[lockerId] ??= [];
    seed[lockerId].push({
      id: unit.id,
      status: mappedStatus,
      temperature: unit.temperature,
      lastUpdated: new Date(),
    });
  }

  // Ensure deterministic ordering by unit id
  for (const lockerId of Object.keys(seed)) {
    seed[lockerId].sort((a, b) => a.id.localeCompare(b.id));
  }

  unitsByLocker = seed;
}

function notify(lockerId: string) {
  const set = listenersByLocker.get(lockerId);
  if (!set || set.size === 0) return;
  const payload = (unitsByLocker[lockerId] ?? []).map((u) => ({ ...u }));
  for (const cb of set) cb(payload);
}

/**
 * Subscribe to real-time locker unit status updates
 * @param lockerId - The locker ID to monitor
 * @param callback - Function called when status changes
 * @returns Unsubscribe function
 */
export function subscribeToLockerUnits(
  lockerId: string,
  callback: (units: LockerUnitStatus[]) => void
): () => void {
  initIfNeeded();

  let set = listenersByLocker.get(lockerId);
  if (!set) {
    set = new Set();
    listenersByLocker.set(lockerId, set);
  }
  set.add(callback);

  // Initial emit
  callback((unitsByLocker[lockerId] ?? []).map((u) => ({ ...u })));

  return () => {
    const current = listenersByLocker.get(lockerId);
    current?.delete(callback);
    if (current && current.size === 0) listenersByLocker.delete(lockerId);
  };
}

/**
 * Reserve a locker unit
 * @param lockerId - The locker ID
 * @param unitId - The unit ID to reserve
 * @returns Promise that resolves when reservation is complete
 */
export async function reserveLockerUnit(
  lockerId: string,
  unitId: string
): Promise<{ success: boolean; reservationId?: string; error?: string }> {
  initIfNeeded();
  const list = unitsByLocker[lockerId] ?? [];
  const idx = list.findIndex((u) => u.id === unitId);
  if (idx < 0) return { success: false, error: "UNIT_NOT_FOUND" };
  if (list[idx].status !== "available") return { success: false, error: "UNIT_NOT_AVAILABLE" };

  list[idx] = { ...list[idx], status: "reserved", lastUpdated: new Date() };
  unitsByLocker[lockerId] = list;
  notify(lockerId);

  return { success: true, reservationId: `res_${Date.now()}` };
}

/**
 * Update locker unit status
 * @param lockerId - The locker ID
 * @param unitId - The unit ID
 * @param status - New status
 */
export async function updateLockerUnitStatus(
  lockerId: string,
  unitId: string,
  status: LockerUnitStatus["status"]
): Promise<void> {
  initIfNeeded();
  const list = unitsByLocker[lockerId] ?? [];
  const idx = list.findIndex((u) => u.id === unitId);
  if (idx < 0) return;
  list[idx] = { ...list[idx], status, lastUpdated: new Date() };
  unitsByLocker[lockerId] = list;
  notify(lockerId);
}
