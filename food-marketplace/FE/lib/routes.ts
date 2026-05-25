export const routes = {
  home: "/",
  itemDetail: (id: string) => `/items/${id}`,
  checkout: (id: string) => `/checkout/${id}`,
  paymentSelect: "/payment/select",
  map: "/map",
  favorites: "/favorites",
  myPage: "/mypage",
  notifications: "/mypage/notifications",
  reviewNew: (orderId: string) => `/reviews/new?order_id=${orderId}`,
  history: "/history",
  historyDetail: (orderId: string) => `/history/${orderId}`,
} as const;
