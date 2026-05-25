import { NextRequest, NextResponse } from 'next/server'

// Routes accessible without authentication
const PUBLIC_ROUTES = ['/login', '/register', '/locker-sim', '/payment/card-callback']

// Route prefixes restricted by role (more specific paths first)
// owner_shop can only access /seller, /locker-sim
// owner_locker can only access /locker-owner, /locker-sim
// customer can only access /, /combos, /orders, /history, /favorites, /lockers, /mypage, /payment, /items, /map
const SELLER_ONLY = ['/seller']
const LOCKER_OWNER_ONLY = ['/locker-owner']
const ADMIN_ONLY = ['/admin']

function redirectToHome(role: string, request: NextRequest) {
  if (role === 'owner_shop') return NextResponse.redirect(new URL('/seller', request.url))
  if (role === 'owner_locker') return NextResponse.redirect(new URL('/locker-owner', request.url))
  if (role === 'admin') return NextResponse.redirect(new URL('/admin', request.url))
  return NextResponse.redirect(new URL('/', request.url))
}

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    // Expired if exp is in the past (with 30s buffer)
    return typeof payload.exp === 'number' && payload.exp < Date.now() / 1000 - 30
  } catch {
    return true
  }
}

function clearAuthAndRedirectToLogin(request: NextRequest, from?: string) {
  const loginUrl = new URL('/login', request.url)
  if (from) loginUrl.searchParams.set('from', from)
  const res = NextResponse.redirect(loginUrl)
  res.cookies.delete('access_token')
  res.cookies.delete('refresh_token')
  res.cookies.delete('user_data')
  return res
}

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname
  const accessToken = request.cookies.get('access_token')?.value
  const userDataStr = request.cookies.get('user_data')?.value

  const isPublicRoute = PUBLIC_ROUTES.some(route => pathname.startsWith(route))

  // No token or expired token → clear cookies and redirect to login
  if (!isPublicRoute && (!accessToken || isTokenExpired(accessToken))) {
    if (!accessToken) {
      const loginUrl = new URL('/login', request.url)
      loginUrl.searchParams.set('from', pathname)
      return NextResponse.redirect(loginUrl)
    }
    return clearAuthAndRedirectToLogin(request, pathname)
  }

  // Already logged in → skip /login and /register
  if (accessToken && (pathname === '/login' || pathname === '/register')) {
    try {
      const userData = userDataStr ? JSON.parse(decodeURIComponent(userDataStr)) : null
      if (userData?.role) return redirectToHome(userData.role, request)
    } catch {}
  }

  // Role-based access control (only block wrong-role access, not missing userData)
  if (accessToken && !isPublicRoute && userDataStr) {
    try {
      const userData = JSON.parse(decodeURIComponent(userDataStr))
      const role = userData?.role
      if (!role) return NextResponse.next()

      // Block non-sellers from /seller
      if (SELLER_ONLY.some(p => pathname.startsWith(p)) && role !== 'owner_shop' && role !== 'admin') {
        return redirectToHome(role, request)
      }

      // Block non-locker-owners from /locker-owner
      if (LOCKER_OWNER_ONLY.some(p => pathname.startsWith(p)) && role !== 'owner_locker' && role !== 'admin') {
        return redirectToHome(role, request)
      }

      // Block non-admins from /admin
      if (ADMIN_ONLY.some(p => pathname.startsWith(p)) && role !== 'admin') {
        return redirectToHome(role, request)
      }
    } catch {
      return clearAuthAndRedirectToLogin(request)
    }
  }

  return NextResponse.next()
}

// Configure which routes to run middleware on
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
}
