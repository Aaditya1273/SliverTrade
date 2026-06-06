'use client'

import { Card } from '@/components/ui/card'
import { AlertTriangle } from 'lucide-react'

export function SignalDisclaimer() {
  return (
    <div className="flex items-start gap-2 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg mt-3">
      <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
      <p className="text-xs text-amber-600 dark:text-amber-400 leading-relaxed">
        <strong>Disclaimer:</strong> This is an algorithmic signal, not financial advice. 
        Trading involves substantial risk of loss. Past signal accuracy does not guarantee future results. 
        SilverTrade AI is not a SEBI-registered investment advisor.
      </p>
    </div>
  )
}
