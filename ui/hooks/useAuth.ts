'use client'

import { useState, useEffect } from 'react'
import { PLATFORM } from '@/lib/api-config'

interface AuthSession {
  /** Whether the user has a valid session */
  authenticated: boolean
  /** Whether broker is connected (logged_in flag) */
  loggedIn: boolean
  /** API key for broker operations — null if no broker connected */
  apiKey: string | null
  /** Username from session */
  user: string | null
  /** Connected broker name */
  broker: string | null
  /** Loading state for initial fetch */
  loading: boolean
  /** Error message if session check failed */
  error: string | null
}

/**
 * Reads the current authentication session from the Platform backend.
 *
 * Calls GET /auth/session-status on mount to determine:
 * - Whether the user is authenticated
 * - Whether a broker is connected
 * - The user's API key (needed for all broker API calls)
 *
 * Components that need the apiKey should use this hook and pass
 * the value down to data-fetching hooks like usePortfolio.
 */
export function useAuth(): AuthSession {
  const [session, setSession] = useState<AuthSession>({
    authenticated: false,
    loggedIn: false,
    apiKey: null,
    user: null,
    broker: null,
    loading: true,
    error: null,
  })

  useEffect(() => {
    let cancelled = false

    async function fetchSession() {
      try {
        const response = await fetch(PLATFORM('/auth/session-status'), {
          method: 'GET',
          credentials: 'include',
          cache: 'no-store',
        })

        if (!response.ok) {
          throw new Error(`Session check returned ${response.status}`)
        }

        const data = await response.json()

        if (!cancelled) {
          setSession({
            authenticated: data.authenticated === true,
            loggedIn: data.logged_in === true,
            apiKey: data.api_key ?? null,
            user: data.user ?? null,
            broker: data.broker ?? null,
            loading: false,
            error: null,
          })
        }
      } catch (err) {
        if (!cancelled) {
          setSession(prev => ({
            ...prev,
            loading: false,
            error: err instanceof Error ? err.message : 'Failed to check session',
          }))
        }
      }
    }

    fetchSession()

    return () => {
      cancelled = true
    }
  }, [])

  return session
}
