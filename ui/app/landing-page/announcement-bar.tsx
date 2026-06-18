'use client'

import { useState } from 'react'
import { X } from 'lucide-react'

export default function AnnouncementBar() {
  const [visible, setVisible] = useState(true)

  if (!visible) return null

  return (
    <div
      className="relative flex items-center justify-center px-4 py-2.5 text-[13px] font-medium tracking-wide"
      style={{ backgroundColor: 'var(--inverse-bg)', color: 'var(--inverse-fg)' }}
    >
      <span className="text-center">
        Early access — free forever plan.{' '}
        <a href="/signup" className="underline hover:no-underline transition-all duration-200">
          Get started
        </a>
      </span>
      <button
        onClick={() => setVisible(false)}
        className="absolute right-4 top-1/2 -translate-y-1/2 p-1 hover:opacity-70 transition-opacity duration-200"
        aria-label="Close announcement"
        style={{ color: 'var(--inverse-fg)' }}
      >
        <X size={16} />
      </button>
    </div>
  )
}
