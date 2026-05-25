export interface AuthUser {
  id: string
  email: string
  name?: string
  role: 'admin' | 'customer' | 'owner_shop' | 'owner_locker'
  icon?: string
}

export function saveAuth(accessToken: string, refreshToken: string, user: AuthUser) {
  localStorage.setItem('access_token', accessToken)
  localStorage.setItem('refresh_token', refreshToken)
  localStorage.setItem('user', JSON.stringify(user))

  const maxAge = 7 * 24 * 60 * 60
  document.cookie = `access_token=${accessToken}; path=/; max-age=${maxAge}; samesite=lax`
  document.cookie = `refresh_token=${refreshToken}; path=/; max-age=${maxAge}; samesite=lax`
  document.cookie = `user_data=${encodeURIComponent(JSON.stringify(user))}; path=/; max-age=${maxAge}; samesite=lax`

  window.dispatchEvent(new Event('auth-changed'))
}

export function getUser(): AuthUser | null {
  if (typeof window === 'undefined') return null
  const raw = localStorage.getItem('user')
  if (!raw) return null
  try { return JSON.parse(raw) } catch { return null }
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('access_token')
}

export function logout() {
  // Remove from localStorage
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')

  // Remove cookies
  document.cookie = 'access_token=; path=/; max-age=0'
  document.cookie = 'refresh_token=; path=/; max-age=0'
  document.cookie = 'user_data=; path=/; max-age=0'

  // Redirect to login
  window.location.href = '/login'
}

export function isLoggedIn(): boolean {
  return !!getToken()
}

export function requireRole(role: string): boolean {
  const user = getUser()
  return user?.role === role
}

/**
 * Refresh access token using refresh token
 * Called when access token is expired
 */
export async function refreshAccessToken(): Promise<boolean> {
  try {
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      logout()
      return false
    }

    const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8001/api'
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })

    if (!response.ok) {
      logout()
      return false
    }

    const data = await response.json()
    if (data.data?.access_token) {
      // Update tokens
      localStorage.setItem('access_token', data.data.access_token)
      document.cookie = `access_token=${data.data.access_token}; path=/; max-age=${7 * 24 * 60 * 60}; samesite=lax`
      return true
    }

    logout()
    return false
  } catch (err) {
    logout()
    return false
  }
}
