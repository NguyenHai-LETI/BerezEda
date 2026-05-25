export const sellerRoutes = {
  home: "/seller",
  itemDetail: (id: string) => `/seller/items/${id}`,
  addItem: "/seller/add-item",
  salesHistory: "/seller/sales-history",
  productManagement: "/seller/product-management",
  profileSettings: "/seller/profile-settings",
  notifications: "/seller/notifications",
} as const;
