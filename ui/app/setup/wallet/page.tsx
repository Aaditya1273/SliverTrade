'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

// Wallet sub-page — broker setup is handled at /setup
export default function WalletSetupPage() {
  const router = useRouter()
  useEffect(() => { router.replace('/setup') }, [router])
  return null
}
