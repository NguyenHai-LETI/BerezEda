// Seller app mock data (no backend)
// Shared lockers come from customer mock.

export interface Locker {
  id: string;
  name: string;
  areaDescription: string;
  boxNo: string;
  distanceKm: number;
  lat: number;
  lng: number;
}

export interface LockerUnit {
  id: string;
  lockerId: string;
  unitNumber: number;
  temperature: number; // Celsius
  status: "available" | "occupied" | "reserved" | "maintenance" | "in_use_by_other";
  boxNo: string;
}

export interface SellerItem {
  id: string;
  title: string;
  description: string;
  images: string[];
  price: number;
  stockQuantity: number;
  shopId: string;
  lockerId: string;
  lockerUnitId?: string;
  status: "active" | "inactive" | "pending" | "sold_out";
  createdAt: Date;
  updatedAt: Date;
}

export interface SaleRecord {
  id: string;
  itemId: string;
  itemTitle: string;
  itemImage: string;
  quantity: number;
  revenue: number;
  saleDate: Date;
  orderStatus: "delivered" | "pending" | "cancelled";
  customerName?: string;
  lockerId: string;
  lockerName: string;
}

export interface SellerNotification {
  id: string;
  message: string;
  dateTime: Date;
  readStatus: boolean;
  type: "order" | "stock" | "system" | "payment";
}

export interface SalesSummary {
  totalSales: number;
  totalRevenue: number;
  activeItems: number;
  pendingOrders: number;
  thisMonthRevenue: number;
  lastMonthRevenue: number;
}

// Re-export lockers from customer mock
import { lockers as customerLockers, getLockerById as getCustomerLockerById } from "./mock";
export const lockers: Locker[] = customerLockers as any;
export const getLockerById = getCustomerLockerById;

export const lockerUnits: LockerUnit[] = [
  // locker1
  { id: "unit1-1", lockerId: "locker1", unitNumber: 1, temperature: 0, status: "available", boxNo: "1" },
  { id: "unit1-2", lockerId: "locker1", unitNumber: 2, temperature: 9, status: "available", boxNo: "2" },
  { id: "unit1-3", lockerId: "locker1", unitNumber: 3, temperature: -10, status: "available", boxNo: "3" },
  { id: "unit1-4", lockerId: "locker1", unitNumber: 4, temperature: -3, status: "available", boxNo: "4" },
  { id: "unit1-5", lockerId: "locker1", unitNumber: 5, temperature: 0, status: "occupied", boxNo: "5" },
  { id: "unit1-6", lockerId: "locker1", unitNumber: 6, temperature: -15, status: "available", boxNo: "6" },
  { id: "unit1-7", lockerId: "locker1", unitNumber: 7, temperature: 15, status: "available", boxNo: "7" },
  { id: "unit1-8", lockerId: "locker1", unitNumber: 8, temperature: -1, status: "in_use_by_other", boxNo: "8" },
  { id: "unit1-9", lockerId: "locker1", unitNumber: 9, temperature: 11, status: "available", boxNo: "9" },
  { id: "unit1-10", lockerId: "locker1", unitNumber: 10, temperature: -14, status: "available", boxNo: "10" },
  { id: "unit1-11", lockerId: "locker1", unitNumber: 11, temperature: 5, status: "occupied", boxNo: "11" },
  { id: "unit1-12", lockerId: "locker1", unitNumber: 12, temperature: -5, status: "available", boxNo: "12" },
  // locker2
  { id: "unit2-1", lockerId: "locker2", unitNumber: 1, temperature: 2, status: "available", boxNo: "1" },
  { id: "unit2-2", lockerId: "locker2", unitNumber: 2, temperature: -8, status: "in_use_by_other", boxNo: "2" },
  { id: "unit2-3", lockerId: "locker2", unitNumber: 3, temperature: 4, status: "available", boxNo: "3" },
  { id: "unit2-4", lockerId: "locker2", unitNumber: 4, temperature: -12, status: "occupied", boxNo: "4" },
  { id: "unit2-5", lockerId: "locker2", unitNumber: 5, temperature: 7, status: "available", boxNo: "5" },
];

export function getLockerUnitsByLockerIdAll(lockerId: string): LockerUnit[] {
  return lockerUnits.filter((u) => u.lockerId === lockerId);
}

export function getLockerUnitById(unitId: string): LockerUnit | undefined {
  return lockerUnits.find((u) => u.id === unitId);
}

const imgBorscht =
  "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=1200&q=60";
const imgPelmeni =
  "https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?auto=format&fit=crop&w=1200&q=60";

export const sellerItems: SellerItem[] = [
  {
    id: "seller-item1",
    title: "Borscht Soup Set",
    description: "Traditional Russian borscht ingredients — beets, cabbage, and carrots. Great for a hearty meal.",
    images: [imgBorscht],
    price: 1800,
    stockQuantity: 14,
    shopId: "shop1",
    lockerId: "locker1",
    lockerUnitId: "unit1-2",
    status: "active",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2),
    updatedAt: new Date(Date.now() - 1000 * 60 * 10),
  },
  {
    id: "seller-item2",
    title: "Pelmeni Pack",
    description: "Hand-made Russian pelmeni (dumplings) filled with minced meat. Serve with smetana.",
    images: [imgPelmeni],
    price: 2800,
    stockQuantity: 6,
    shopId: "shop1",
    lockerId: "locker2",
    lockerUnitId: "unit2-1",
    status: "pending",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24),
    updatedAt: new Date(Date.now() - 1000 * 60 * 30),
  },
];

export const salesSummary: SalesSummary = {
  totalSales: 14,
  totalRevenue: 306_634,
  activeItems: sellerItems.filter((i) => i.status === "active").length,
  pendingOrders: 2,
  thisMonthRevenue: 306_634,
  lastMonthRevenue: 280_120,
};

export const salesHistory: SaleRecord[] = [
  {
    id: "sale1",
    itemId: "seller-item1",
    itemTitle: "Borscht Soup Set",
    itemImage: imgBorscht,
    quantity: 2,
    revenue: 3600,
    saleDate: new Date(Date.now() - 1000 * 60 * 60 * 5),
    orderStatus: "delivered",
    customerName: "Customer A",
    lockerId: "locker1",
    lockerName: "Okhotny Ryad Locker A",
  },
];

export const sellerNotifications: SellerNotification[] = [
  {
    id: "notif1",
    message: "New order received for Borscht Soup Set.",
    dateTime: new Date(Date.now() - 1000 * 60 * 12),
    readStatus: false,
    type: "order",
  },
];

export function getSellerItemById(id: string): SellerItem | undefined {
  return sellerItems.find((i) => i.id === id);
}

export function getSaleById(id: string): SaleRecord | undefined {
  return salesHistory.find((s) => s.id === id);
}
