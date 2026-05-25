export const APP_NAME = 'БережЕда'
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const DISCOUNT_RATES = [30, 40, 50] as const

export const COMBO_STATUS_LABELS: Record<string, string> = {
  draft: 'Черновик',
  available: 'В продаже',
  sold: 'Продан',
  expired: 'Время истекло',
  cancelled: 'Отменён',
}

export const ORDER_STATUS_LABELS: Record<string, string> = {
  pending: 'Ожидает оплаты',
  paid: 'Оплачен',
  completed: 'Получен',
  cancelled: 'Отменён',
  expired: 'Истёк срок',
}

export const LOCKER_STATUS_LABELS: Record<string, string> = {
  available: 'Свободен',
  occupied: 'Занят',
  reserved: 'Зарезервирован',
  maintenance: 'Обслуживание',
}

export const ROLES = {
  ADMIN: 'admin',
  CUSTOMER: 'customer',
  SHOP_OWNER: 'owner_shop',
  LOCKER_OWNER: 'owner_locker',
} as const
