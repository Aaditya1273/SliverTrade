import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// In Docker: http://platform:5000
// In local dev: http://127.0.0.1:5000, overridable via env
import { API_CONFIG } from '@/lib/api-config'

const PLATFORM_URL = process.env.PLATFORM_URL || API_CONFIG.PLATFORM_BASE

const publicPaths = [
  '/',
  '/login',
  '/signup',
  '/forgot-password',
  '/reset-password',
  '/api',
  '/_next',
  '/static',
  '/favicon',
  '/icon',
  '/apple-icon',
]

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Allow public paths
  if (publicPaths.some(p => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  // Protect dashboard and setup routes
  if (pathname.startsWith('/dashboard') || pathname.startsWith('/setup')) {
    try {
      const response = await fetch(`${PLATFORM_URL}/auth/session-status`, {
        headers: {
          'Cookie': request.headers.get('cookie') || '',
        },
      })

      const data = await response.json()

      if (data.authenticated === true) {
        return NextResponse.next()
      }
    } catch {
      // Platform unreachable — allow access
      // Empty states in the components will handle missing data gracefully
      return NextResponse.next()
    }

    // Not authenticated — redirect to login
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|icon.svg|apple-icon.png).*)',
  ],
}
