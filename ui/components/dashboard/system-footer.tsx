'use client'

import { useSystemHealth, SystemStatusDot } from '@/hooks/useSystemHealth'

export function SystemFooter() {
  const systemHealth = useSystemHealth()

  return (
    <footer className="fixed bottom-0 left-0 right-0 h-8 bg-card/80 backdrop-blur-md border-t border-border flex items-center justify-between px-4 z-50 ml-0 md:ml-64">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <SystemStatusDot status={systemHealth.platform} />
          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
            Platform: {systemHealth.platform}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <SystemStatusDot status={systemHealth.strategy} />
          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
            AI Engine: {systemHealth.strategy}
          </span>
        </div>
        <div className="hidden sm:flex items-center gap-1.5">
          <SystemStatusDot status={systemHealth.data} />
          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
            Data Feed: {systemHealth.data}
          </span>
        </div>
      </div>
      <div className="text-[10px] text-muted-foreground uppercase tracking-wider font-mono">
        {systemHealth.lastUpdated}
      </div>
    </footer>
  )
}
