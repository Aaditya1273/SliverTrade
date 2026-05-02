import { Bell, Settings, EyeOff, Eye } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface DashboardHeaderProps {
  hideBalances: boolean
  setHideBalances: (hide: boolean) => void
}

export function DashboardHeader({ hideBalances, setHideBalances }: DashboardHeaderProps) {
  return (
    <header className="hidden md:flex border-b border-border px-6 lg:px-8 h-16 items-center justify-between bg-card/30 backdrop-blur-sm sticky top-0 z-30">
      <div className="text-sm text-muted-foreground">
        Last updated: Just now
      </div>
      
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setHideBalances(!hideBalances)}
          className="text-muted-foreground hover:text-foreground"
        >
          {hideBalances ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
        </Button>
        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
          <Bell className="w-5 h-5" />
        </Button>
        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
          <Settings className="w-5 h-5" />
        </Button>
      </div>
    </header>
  )
}
