export interface Shop {
  id: string;
  name: string;
  rating: number;
  reviewsCount: number;
}

export interface Locker {
  id: string;
  name: string;
  areaDescription: string;
  boxNo: string;
  distanceKm: number;
  lat?: number;
  lng?: number;
}

export interface ItemContent {
  id: string;
  name: string;
  qty: number;
  unitPriceRUB: number;
  thumbnailUrl: string;
}

export interface Item {
  id: string;
  title: string;
  description: string;
  images: string[];
  originalPriceRUB: number;
  salePriceRUB: number;
  countdownSeconds: number;
  shopId: string;
  lockerId: string;
  contents: ItemContent[];
}

export interface PaymentCard {
  id: string;
  brand: "VISA" | "MASTERCARD" | "AMEX";
  last4: string;
  expiry: string; // "MM/YY"
  isDefault: boolean;
}

export interface PurchaseHistory {
  id: string;
  itemId: string;
  itemTitle: string;
  itemImage: string;
  purchaseDate: Date;
  status: "pending" | "received" | "cancelled";
  lockerId: string;
  lockerName: string;
}

export const shops: Shop[] = [
  { id: "shop1", name: "Moscow Fresh Market", rating: 4.5, reviewsCount: 128 },
  { id: "shop2", name: "Russkiy Produkty", rating: 4.2, reviewsCount: 89 },
  { id: "shop3", name: "Organic Russia", rating: 4.8, reviewsCount: 256 },
  { id: "shop4", name: "Stolovaya Express", rating: 4.0, reviewsCount: 45 },
];

export const lockers: Locker[] = [
  {
    id: "locker1",
    name: "Okhotny Ryad Locker A",
    areaDescription: "Okhotny Ryad, Moscow",
    boxNo: "A-12",
    distanceKm: 0.5,
    lat: 55.7560,
    lng: 37.6182,
  },
  {
    id: "locker2",
    name: "Arbatskaya Locker B",
    areaDescription: "Arbat, Moscow",
    boxNo: "B-05",
    distanceKm: 1.2,
    lat: 55.7519,
    lng: 37.6024,
  },
  {
    id: "locker3",
    name: "Lubyanka Station Locker",
    areaDescription: "Lubyanka, Moscow",
    boxNo: "C-18",
    distanceKm: 2.5,
    lat: 55.7576,
    lng: 37.6259,
  },
  {
    id: "locker4",
    name: "Tverskaya Locker",
    areaDescription: "Tverskaya, Moscow",
    boxNo: "D-03",
    distanceKm: 3.8,
    lat: 55.7654,
    lng: 37.6066,
  },
];

export const items: Item[] = [
  {
    id: "item1",
    title: "Borscht Soup Set",
    description: "Traditional Russian borscht ingredients including fresh beets, cabbage, carrots, and onions. Perfect for cooking a hearty and warming Russian beet soup.",
    images: [
      "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=1200&q=60",
    ],
    originalPriceRUB: 2500,
    salePriceRUB: 1800,
    countdownSeconds: 3600,
    shopId: "shop1",
    lockerId: "locker1",
    contents: [
      {
        id: "content1",
        name: "Fresh Beets",
        qty: 5,
        unitPriceRUB: 200,
        thumbnailUrl: "https://images.unsplash.com/photo-1593105544559-ecb03bf76f82?auto=format&fit=crop&w=200&q=60",
      },
      {
        id: "content2",
        name: "White Cabbage",
        qty: 2,
        unitPriceRUB: 150,
        thumbnailUrl: "https://images.unsplash.com/photo-1518977822534-7049a61ee0c2?auto=format&fit=crop&w=200&q=60",
      },
    ],
  },
  {
    id: "item2",
    title: "Pelmeni Pack",
    description: "Hand-made Russian pelmeni (dumplings) filled with seasoned minced meat. Ready to boil — serve with smetana (sour cream) for an authentic Russian meal.",
    images: [
      "https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?auto=format&fit=crop&w=1200&q=60",
    ],
    originalPriceRUB: 3500,
    salePriceRUB: 2800,
    countdownSeconds: 7200,
    shopId: "shop2",
    lockerId: "locker2",
    contents: [
      {
        id: "content3",
        name: "Pelmeni (500g)",
        qty: 6,
        unitPriceRUB: 300,
        thumbnailUrl: "https://images.unsplash.com/photo-1596797038530-2c107229654b?auto=format&fit=crop&w=200&q=60",
      },
    ],
  },
  {
    id: "item3",
    title: "Blini with Smetana",
    description: "Fresh Russian blini (thin pancakes) served with smetana (sour cream). A classic Russian breakfast and snack — light, soft, and delicious.",
    images: [
      "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?auto=format&fit=crop&w=1200&q=60",
    ],
    originalPriceRUB: 1200,
    salePriceRUB: 900,
    countdownSeconds: 1800,
    shopId: "shop3",
    lockerId: "locker1",
    contents: [
      {
        id: "content4",
        name: "Smetana (sour cream)",
        qty: 1,
        unitPriceRUB: 900,
        thumbnailUrl: "https://images.unsplash.com/photo-1563636619-e9143da7973b?auto=format&fit=crop&w=200&q=60",
      },
    ],
  },
  {
    id: "item4",
    title: "Borodinsky Bread Bundle",
    description: "Dark rye Borodinsky bread, kefir, and traditional Russian condiments. Staple foods straight from the Russian kitchen — hearty and nutritious.",
    images: [
      "https://images.unsplash.com/photo-1589367920969-ab8e050bbb04?auto=format&fit=crop&w=1200&q=60",
    ],
    originalPriceRUB: 2800,
    salePriceRUB: 2200,
    countdownSeconds: 5400,
    shopId: "shop4",
    lockerId: "locker3",
    contents: [
      {
        id: "content5",
        name: "Borodinsky Bread",
        qty: 1,
        unitPriceRUB: 300,
        thumbnailUrl: "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=200&q=60",
      },
      {
        id: "content6",
        name: "Kefir",
        qty: 2,
        unitPriceRUB: 200,
        thumbnailUrl: "https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=200&q=60",
      },
    ],
  },
];

export const paymentCards: PaymentCard[] = [
  {
    id: "card1",
    brand: "VISA",
    last4: "1111",
    expiry: "12/25",
    isDefault: true,
  },
  {
    id: "card2",
    brand: "VISA",
    last4: "2222",
    expiry: "06/26",
    isDefault: false,
  },
  {
    id: "card3",
    brand: "MASTERCARD",
    last4: "3333",
    expiry: "09/25",
    isDefault: false,
  },
];

export const purchaseHistory: PurchaseHistory[] = [
  {
    id: "order1",
    itemId: "item1",
    itemTitle: "Borscht Soup Set",
    itemImage: "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=200&q=60",
    purchaseDate: new Date(2024, 0, 15, 14, 30),
    status: "received",
    lockerId: "locker1",
    lockerName: "Okhotny Ryad Locker A",
  },
  {
    id: "order2",
    itemId: "item2",
    itemTitle: "Pelmeni Pack",
    itemImage: "https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?auto=format&fit=crop&w=200&q=60",
    purchaseDate: new Date(2024, 0, 20, 10, 15),
    status: "received",
    lockerId: "locker2",
    lockerName: "Arbatskaya Locker B",
  },
  {
    id: "order3",
    itemId: "item3",
    itemTitle: "Blini with Smetana",
    itemImage: "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?auto=format&fit=crop&w=200&q=60",
    purchaseDate: new Date(2024, 1, 5, 16, 45),
    status: "received",
    lockerId: "locker1",
    lockerName: "Okhotny Ryad Locker A",
  },
];

export function getShopById(id: string): Shop | undefined {
  return shops.find((s) => s.id === id);
}

export function getLockerById(id: string): Locker | undefined {
  return lockers.find((l) => l.id === id);
}

export function getItemById(id: string): Item | undefined {
  return items.find((i) => i.id === id);
}

export function getPaymentCardById(id: string): PaymentCard | undefined {
  return paymentCards.find((c) => c.id === id);
}
