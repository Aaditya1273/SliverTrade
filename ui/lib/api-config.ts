/**
 * Centralized API URL configuration
 *
 * Single source of truth for all backend service URLs.
 * Every component must import from here — no hardcoded URL strings.
 *
 * In local dev these default to localhost ports.
 * In production, set NEXT_PUBLIC_* env variables via Docker/CI.
 */

export const API_CONFIG = {
  PLATFORM_BASE: process.env.NEXT_PUBLIC_PLATFORM_URL ?? 'http://127.0.0.1:5000',
  STRATEGY_BASE: process.env.NEXT_PUBLIC_STRATEGY_URL ?? 'http://127.0.0.1:5007',
  DATA_BASE:     process.env.NEXT_PUBLIC_DATA_URL     ?? 'http://127.0.0.1:5005',
  WS_BASE:       process.env.NEXT_PUBLIC_WS_URL       ?? 'ws://127.0.0.1:8765',
} as const

export const PLATFORM = (path: string) => `${API_CONFIG.PLATFORM_BASE}${path}`
export const STRATEGY = (path: string) => `${API_CONFIG.STRATEGY_BASE}${path}`
export const DATA     = (path: string) => `${API_CONFIG.DATA_BASE}${path}`
