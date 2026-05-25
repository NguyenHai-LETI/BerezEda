const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api'

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('access_token')
}

async function doFetch(path: string, options: RequestInit, token: string | null) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = 'Bearer ' + token
  return fetch(BASE_URL + path, { ...options, headers })
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let token = getToken()
  let res = await doFetch(path, options, token)

  if (res.status === 401) {
    const rt = typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null
    if (rt) {
      try {
        const rr = await fetch(BASE_URL + '/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: rt }),
        })
        if (rr.ok) {
          const rj = await rr.json()
          const nt = rj?.data?.access_token
          if (nt) {
            localStorage.setItem('access_token', nt)
            // Also update cookie for middleware
            document.cookie = `access_token=${nt}; path=/; max-age=${7 * 24 * 60 * 60}; samesite=strict`
            token = nt
            res = await doFetch(path, options, token)
          }
        }
      } catch {}
    }
    if (res.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        // Also remove cookies
        document.cookie = 'access_token=; path=/; max-age=0'
        document.cookie = 'refresh_token=; path=/; max-age=0'
        document.cookie = 'user_data=; path=/; max-age=0'
        window.location.href = '/login'
      }
      throw new Error('Session expired')
    }
  }

  const json = await res.json()
  if (!res.ok) throw new Error(json.detail || json.message || 'Server error')
  return json
}

export async function login(email: string, password: string) {
  // Call API directly — bypass request() to avoid auto-redirect on 401
  const res = await fetch(BASE_URL + '/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.detail || json.message || 'Ошибка входа')
  return {
    data: {
      access: json.data?.access_token,
      refresh: json.data?.refresh_token,
      user: json.data?.user,
    }
  }
}

export async function register(email: string, password: string, name: string) {
  const response = await request<any>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, name }),
  })
  return {
    data: {
      access: response.data?.access_token,
      refresh: response.data?.refresh_token,
      user: response.data?.user,
    }
  }
}

export async function getMe() {
  return request<any>('/users/me')
}

export async function updateMe(data: { name?: string; phone?: string; birthday?: string; gender?: string }) {
  return request<any>('/users/me', { method: 'PUT', body: JSON.stringify(data) })
}

export async function uploadAvatar(file: File): Promise<any> {
  const token = getToken()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/users/me/avatar`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.message || 'Upload error')
  return json
}

// ── Admin: user management ────────────────────────────
export async function adminCreateUser(email: string, password: string, name: string, role: string) {
  return request<any>('/users/register-by-admin', {
    method: 'POST',
    body: JSON.stringify({ email, password, name, role }),
  })
}

export async function getUsersByRole(role: string) {
  return request<any>(`/users/by-role/${role}`)
}

// ── Lockers ───────────────────────────────────────────
export async function getLockers(params?: { lat?: number; lon?: number }) {
  const q = params ? '?' + new URLSearchParams(params as any).toString() : ''
  return request<any>(`/lockers${q}`)
}

export async function getLocker(id: string) {
  return request<any>(`/lockers/${id}`)
}

export async function getFavoriteLockers() {
  return request<any>('/lockers/favorites')
}

export async function addFavoriteLocker(lockerLocationId: string) {
  return request<any>(`/lockers/favorites?locker_location_id=${lockerLocationId}`, { method: 'POST' })
}

export async function removeFavoriteLocker(favoriteId: string) {
  return request<any>(`/lockers/favorites/${favoriteId}`, { method: 'DELETE' })
}

// ── Combos ────────────────────────────────────────────
export async function getCombos(params?: { locker_location_id?: string; shop_id?: string }) {
  const q = params ? '?' + new URLSearchParams(params as any).toString() : ''
  return request<any>(`/combos${q}`)
}

export async function getCombo(id: string) {
  return request<any>(`/combos/${id}`)
}

export async function getMyCombos(status?: string) {
  const q = status ? `?status=${status}` : ''
  return request<any>(`/combos/my${q}`)
}

export async function createCombo(data: any) {
  return request<any>('/combos', { method: 'POST', body: JSON.stringify(data) })
}

export async function assignComboLocker(comboId: string, data: { locker_unit_id: string; locker_location_id: string }) {
  return request<any>(`/combos/${comboId}/assign-locker`, { method: 'PUT', body: JSON.stringify(data) })
}

export async function confirmComboPlaced(comboId: string) {
  return request<any>(`/combos/${comboId}/confirm-placed`, { method: 'PUT' })
}

export async function updateCombo(comboId: string, data: any) {
  return request<any>(`/combos/${comboId}`, { method: 'PUT', body: JSON.stringify(data) })
}

export async function uploadComboImage(comboId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const token = getToken()
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = 'Bearer ' + token
  const res = await fetch(`${BASE_URL}/combos/${comboId}/image`, {
    method: 'POST',
    headers,
    body: formData,
  })
  if (!res.ok) throw new Error('Ошибка загрузки изображения')
  return res.json()
}

export async function cancelCombo(comboId: string) {
  return request<any>(`/combos/${comboId}/cancel`, { method: 'PUT' })
}

// ── Shops ─────────────────────────────────────────────
export async function getShops(params?: { locker_location_id?: string; search?: string }) {
  const q = params ? '?' + new URLSearchParams(params as any).toString() : ''
  return request<any>(`/shops${q}`)
}

export async function getShop(id: string) {
  return request<any>(`/shops/${id}`)
}

export async function getMyShop() {
  return request<any>('/shops/my')
}

export async function createShop(data: any) {
  return request<any>('/shops', { method: 'POST', body: JSON.stringify(data) })
}

export async function updateShop(id: string, data: any) {
  return request<any>(`/shops/${id}`, { method: 'PUT', body: JSON.stringify(data) })
}

// ── Products ──────────────────────────────────────────
export async function getMyProducts() {
  return request<any>('/products')
}

export async function createProduct(data: any) {
  return request<any>('/products', { method: 'POST', body: JSON.stringify(data) })
}

export async function updateProduct(id: string, data: any) {
  return request<any>(`/products/${id}`, { method: 'PUT', body: JSON.stringify(data) })
}

export async function deleteProduct(id: string) {
  return request<any>(`/products/${id}`, { method: 'DELETE' })
}

export async function uploadProductImage(productId: string, file: File) {
  const token = getToken()
  const form = new FormData()
  form.append('file', file)
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = 'Bearer ' + token
  const res = await fetch(BASE_URL + `/products/${productId}/image`, {
    method: 'POST',
    headers,
    body: form,
  })
  if (!res.ok) {
    const j = await res.json().catch(() => ({}))
    throw new Error(j.message || 'Upload failed')
  }
  return res.json()
}

// ── Orders ────────────────────────────────────────────
export async function createOrder(comboId: string) {
  return request<any>('/orders/', { method: 'POST', body: JSON.stringify({ combo_id: comboId }) })
}

export async function getOrders(year?: number, month?: number) {
  const params: any = {}
  if (year) params.year = year
  if (month) params.month = month
  const q = Object.keys(params).length ? '?' + new URLSearchParams(params).toString() : ''
  return request<any>(`/orders${q}`)
}

export async function getOrder(id: string) {
  return request<any>(`/orders/${id}`)
}

export async function pickupOrder(id: string, accessCode: string) {
  return request<any>(`/orders/${id}/pickup`, {
    method: 'POST',
    body: JSON.stringify({ access_code: accessCode }),
  })
}

// ── Payments / Fincode ────────────────────────────────
export async function registerFincodeCustomer() {
  return request<any>('/purchase/customers/register', { method: 'POST' })
}

export async function getCards() {
  // Returns SuccessResponse wrapping a ListResponse
  const res = await request<any>('/purchase/cards/list')
  // Unwrap nested data: res.data.data is the array
  return { data: res?.data?.data ?? res?.data ?? [] }
}

export async function addCard(comboId?: string) {
  const qs = comboId ? `?combo_id=${encodeURIComponent(comboId)}` : ''
  return request<any>(`/purchase/card/register${qs}`, { method: 'POST' })
}

export async function deleteCard(cardId: string) {
  return request<any>(`/purchase/card/delete/${cardId}`, { method: 'DELETE' })
}

export async function setDefaultCard(cardId: string) {
  return request<any>(`/purchase/cards/set-default/${cardId}`, { method: 'POST' })
}

export async function executePayment(orderId: string, cardId: string) {
  return request<any>('/purchase/payment', {
    method: 'POST',
    body: JSON.stringify({ order_id: orderId, card_id: cardId }),
  })
}

// ── Favorites ─────────────────────────────────────────
export async function getFavoriteShops() {
  return request<any>('/favorites/shops')
}

export async function addFavoriteShop(shopId: string) {
  return request<any>('/favorites/shops', { method: 'POST', body: JSON.stringify({ shop_id: shopId }) })
}

export async function removeFavoriteShop(shopId: string) {
  return request<any>(`/favorites/shops/${shopId}`, { method: 'DELETE' })
}

// ── Reviews ───────────────────────────────────────────
export async function getShopReviews(shopId: string) {
  return request<any>(`/reviews/shop/${shopId}`)
}

export async function createReview(data: { order_id: string; rating: number; comment?: string }) {
  return request<any>('/reviews', { method: 'POST', body: JSON.stringify(data) })
}

export async function getMyShopReviews() {
  return request<any>('/reviews/mine')
}

export async function getReviewForOrder(orderId: string) {
  return request<any>(`/reviews/order/${orderId}`)
}

// ── Notifications ─────────────────────────────────────
export async function getNotifications() {
  return request<any>('/notifications')
}

export async function markNotificationRead(id: string) {
  return request<any>(`/notifications/${id}/read`, { method: 'PUT' })
}

export async function markAllNotificationsRead() {
  return request<any>('/notifications/read-all', { method: 'PUT' })
}

// ── Sales ─────────────────────────────────────────────
export async function getSalesHistory(date?: string) {
  const q = date ? `?date_str=${date}` : ''
  return request<any>(`/sales/history${q}`)
}

export async function getUnsoldCombos() {
  return request<any>('/sales/unsold')
}

export async function getMonthlySummary(year?: number, month?: number) {
  const params: any = {}
  if (year) params.year = year
  if (month) params.month = month
  const q = Object.keys(params).length ? '?' + new URLSearchParams(params).toString() : ''
  return request<any>(`/sales/summary${q}`)
}

// ── Devices (FCM) ─────────────────────────────────────
export async function registerDevice(fcmToken: string) {
  return request<any>('/devices', {
    method: 'POST',
    body: JSON.stringify({ fcm_token: fcmToken, platform: 'web' }),
  })
}

// ── Upload helper ─────────────────────────────────────
export async function uploadFile(path: string, file: File): Promise<any> {
  const token = getToken()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.message || 'Upload error')
  return json
}

// ── Seller: Shop image upload ─────────────────────────
export async function uploadShopImage(shopId: string, form: FormData): Promise<any> {
  const token = getToken()
  const res = await fetch(`${BASE_URL}/shops/${shopId}/image`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.message || 'Upload error')
  return json
}

// ── Seller: My lockers ────────────────────────────────
export async function getMyLockers() {
  return request<any>('/shops/my/lockers')
}

// ── Sales: Summary ────────────────────────────────────
export async function getSalesSummary(period?: 'week' | 'month' | 'quarter' | 'year') {
  const params: Record<string, string> = {}
  const now = new Date()
  if (period === 'week') {
    const from = new Date(now); from.setDate(from.getDate() - 7)
    params.date_from = from.toISOString().split('T')[0]
    params.date_to = now.toISOString().split('T')[0]
  } else if (period === 'quarter') {
    const from = new Date(now); from.setMonth(from.getMonth() - 3)
    params.date_from = from.toISOString().split('T')[0]
    params.date_to = now.toISOString().split('T')[0]
  } else if (period === 'year') {
    params.year = String(now.getFullYear())
  } else {
    params.year = String(now.getFullYear())
    params.month = String(now.getMonth() + 1)
  }
  const q = Object.keys(params).length ? '?' + new URLSearchParams(params).toString() : ''
  return request<any>(`/sales/summary${q}`)
}

// ── Notifications: My ─────────────────────────────────
export async function getMyNotifications() {
  return request<any>('/notifications')
}

// ── Locker owner: Locker locations CRUD ───────────────
export async function getLockerLocation(id: string) {
  return request<any>(`/lockers/${id}`)
}

export async function getMyLockerLocations() {
  return request<any>('/lockers/owner/my')
}

export async function createLockerLocation(data: any) {
  return request<any>('/lockers', { method: 'POST', body: JSON.stringify(data) })
}

export async function updateLockerLocation(id: string, data: any) {
  return request<any>(`/lockers/${id}`, { method: 'PUT', body: JSON.stringify(data) })
}

export async function deleteLockerLocation(id: string) {
  return request<any>(`/lockers/${id}`, { method: 'DELETE' })
}

export async function getLockerUnits(lockerLocationId: string) {
  return request<any>(`/lockers/${lockerLocationId}/units`)
}

export async function createLockerUnit(lockerLocationId: string, data: any) {
  return request<any>(`/lockers/${lockerLocationId}/units`, { method: 'POST', body: JSON.stringify(data) })
}

export async function updateLockerUnit(lockerLocationId: string, unitId: string, data: any) {
  return request<any>(`/lockers/${lockerLocationId}/units/${unitId}`, { method: 'PUT', body: JSON.stringify(data) })
}

export async function deleteLockerUnit(lockerLocationId: string, unitId: string) {
  return request<any>(`/lockers/${lockerLocationId}/units/${unitId}`, { method: 'DELETE' })
}

export async function syncLockersToFirebase() {
  return request<any>('/lockers/sync-firebase', { method: 'POST' })
}

export async function addShopToLocker(lockerLocationId: string, shopId: string) {
  return request<any>(`/shops/${shopId}/lockers`, {
    method: 'POST',
    body: JSON.stringify({ locker_location_id: lockerLocationId }),
  })
}

export async function getLockerShops(lockerLocationId: string) {
  return request<any>(`/lockers/${lockerLocationId}/shops`)
}

export async function importLockerUnitsCsv(lockerLocationId: string, file: File): Promise<any> {
  const token = getToken()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/lockers/${lockerLocationId}/units/import-csv`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.message || 'Import error')
  return json
}

export async function uploadLockerImage(lockerLocationId: string, file: File): Promise<any> {
  const token = getToken()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/lockers/${lockerLocationId}/image`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.message || 'Upload error')
  return json
}

// ── Locker Simulator ──────────────────────────────────
export async function lockerSimPickup(accessCode: string) {
  return request<any>('/orders/sim-pickup', {
    method: 'POST',
    body: JSON.stringify({ access_code: accessCode }),
  })
}

export async function getOrderByAccessCode(accessCode: string) {
  const orders = await getOrders()
  const all: any[] = orders.data || []
  return all.find((o: any) => o.access_code === accessCode && o.status === 'paid') || null
}
