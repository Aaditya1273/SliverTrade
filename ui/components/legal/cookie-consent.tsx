'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { X } from 'lucide-react'

export function CookieConsent() {
  const [showBanner, setShowBanner] = useState(false)
  const [choice, setChoice] = useState<string | null>(null)

  useEffect(() => {
    // Check if user has already made a choice
    const storedChoice = localStorage.getItem('cookieConsent')
    if (!storedChoice) {
      setShowBanner(true)
    } else {
      setChoice(storedChoice)
      // Load analytics if user accepted all
      if (storedChoice === 'all') {
        // TODO: Initialize analytics
      }
    }
  }, [])

  const handleAcceptAll = () => {
    localStorage.setItem('cookieConsent', 'all')
    setChoice('all')
    setShowBanner(false)
    // TODO: Initialize analytics
  }

  const handleEssentialOnly = () => {
    localStorage.setItem('cookieConsent', 'essential')
    setChoice('essential')
    setShowBanner(false)
  }

  if (!showBanner) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 bg-background border-t border-border">
      <Card className="max-w-4xl mx-auto p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          This site uses cookies for authentication and analytics.
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.open('/legal/privacy', '_blank')}
          >
            Privacy Policy
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleEssentialOnly}
          >
            Essential Only
          </Button>
          <Button
            size="sm"
            onClick={handleAcceptAll}
          >
            Accept All
          </Button>
        </div>
      </Card>
    </div>
  )
}
