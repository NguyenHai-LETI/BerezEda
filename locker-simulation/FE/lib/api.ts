const BASE = process.env.NEXT_PUBLIC_LOCKER_SIM_API || 'http://localhost:8001/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.message || `HTTP ${res.status}`)
  return json as T
}

export interface ValidateQRResponse {
  valid: boolean
  code_type?: string
  locker_unit_id?: string
  location_id?: string
  combo_id?: string
  order_id?: string
  code?: string
  message: string
}

export interface SimulateActionResponse {
  success: boolean
  message: string
  system1_response?: Record<string, unknown>
}

export function validateQR(qr_code: string): Promise<ValidateQRResponse> {
  return request('/qr/validate', {
    method: 'POST',
    body: JSON.stringify({ qr_code }),
  })
}

export function confirmDeposit(code: string): Promise<SimulateActionResponse> {
  return request('/simulate/deposit-confirmed', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
}

export function confirmPickup(code: string): Promise<SimulateActionResponse> {
  return request('/simulate/pickup-confirmed', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
}
