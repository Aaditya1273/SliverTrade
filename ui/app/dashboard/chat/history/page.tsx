'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Brain, History, MessageSquare, Search, Clock, ArrowRight } from 'lucide-react'
import { PLATFORM } from '@/lib/api-config'
import { useAuth } from '@/hooks/useAuth'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { toast } from 'sonner'

const PLATFORM_BASE = PLATFORM('/api/v1')

interface Conversation {
  id: number
  conversation_id: string
  title: string
  messages: Array<{ role: string; content: string; timestamp?: string }>
  created_at: string
  updated_at: string
}

export default function ChatHistoryPage() {
  const { apiKey } = useAuth()
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch conversations
  const { data, isLoading, error } = useQuery({
    queryKey: ['chat-conversations'],
    queryFn: async () => {
      if (!apiKey) throw new Error('No API key')
      const response = await axios.get(`${PLATFORM_BASE}/chat/conversations`, {
        params: { apikey: apiKey },
      })
      return response.data.data as Conversation[]
    },
    enabled: !!apiKey,
  })

  const conversations = data || []
  const messageCount = conversations.reduce((sum, c) => sum + (c.messages?.length || 0), 0)

  // Filter by search
  const filteredConversations = searchQuery
    ? conversations.filter(c =>
        c.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.messages?.some(m => m.content?.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : conversations

  if (!apiKey) {
    return (
      <main className="min-h-screen bg-background text-foreground">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Card className="p-12 border-border text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-accent/10 flex items-center justify-center">
              <History className="w-8 h-8 text-accent" />
            </div>
            <h2 className="text-xl font-semibold mb-2">No Chat History Available</h2>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Connect a broker to start using the AI trading assistant. Your conversations will appear here.
            </p>
            <Link
              href="/setup"
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-accent text-accent-foreground font-medium hover:opacity-90 transition-opacity"
            >
              Connect Broker
              <ArrowRight className="w-4 h-4" />
            </Link>
          </Card>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <History className="w-6 h-6 text-accent" />
              <h1 className="text-3xl font-bold">Chat History</h1>
            </div>
            <p className="text-muted-foreground">
              {isLoading
                ? 'Loading conversations...'
                : `${conversations.length} conversation${conversations.length !== 1 ? 's' : ''} · ${messageCount} message${messageCount !== 1 ? 's' : ''}`
              }
            </p>
          </div>
          <Link href="/dashboard/chat">
            <Button variant="default" className="gap-2">
              <MessageSquare className="w-4 h-4" />
              New Chat
            </Button>
          </Link>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations by title or content..."
            className="pl-10 bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
          />
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="p-6 border-border animate-pulse">
                <div className="h-5 bg-card/50 rounded w-3/4 mb-3" />
                <div className="h-3 bg-card/50 rounded w-1/2 mb-2" />
                <div className="h-3 bg-card/50 rounded w-1/3" />
              </Card>
            ))}
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <Card className="p-8 border-border text-center">
            <p className="text-muted-foreground mb-4">Failed to load chat history.</p>
            <Button
              variant="outline"
              onClick={() => queryClient.invalidateQueries({ queryKey: ['chat-conversations'] })}
            >
              Try Again
            </Button>
          </Card>
        )}

        {/* Empty State */}
        {!isLoading && !error && filteredConversations.length === 0 && (
          <Card className="p-12 border-border text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-accent/10 flex items-center justify-center">
              <Brain className="w-8 h-8 text-accent" />
            </div>
            <h2 className="text-xl font-semibold mb-2">
              {searchQuery ? 'No Matches Found' : 'No Conversations Yet'}
            </h2>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              {searchQuery
                ? `No conversations match "${searchQuery}". Try a different search term.`
                : 'Start a chat with the AI trading assistant to get personalized trading insights and advice.'
              }
            </p>
            <Link href="/dashboard/chat">
              <Button className="gap-2">
                <MessageSquare className="w-4 h-4" />
                Start a Conversation
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </Card>
        )}

        {/* Conversations List */}
        {!isLoading && !error && filteredConversations.length > 0 && (
          <div className="space-y-3">
            {filteredConversations.map((conv) => {
              const messagePreview = conv.messages?.find(m => m.role === 'user')?.content
              const messageCount = conv.messages?.length || 0
              const date = new Date(conv.updated_at || conv.created_at)
              const isToday = new Date().toDateString() === date.toDateString()
              const isYesterday = new Date(Date.now() - 86400000).toDateString() === date.toDateString()
              const dateStr = isToday
                ? `Today at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
                : isYesterday
                  ? `Yesterday at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
                  : date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })

              return (
                <Link
                  key={conv.conversation_id}
                  href={`/dashboard/chat?conversation_id=${encodeURIComponent(conv.conversation_id)}`}
                  className="block"
                >
                  <Card className="p-5 border-border hover:border-accent/30 hover:bg-card/50 transition-all group cursor-pointer">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1.5">
                          <MessageSquare className="w-4 h-4 text-accent flex-shrink-0" />
                          <h3 className="font-medium truncate">
                            {conv.title || 'Untitled Conversation'}
                          </h3>
                          {searchQuery && conv.title?.toLowerCase().includes(searchQuery.toLowerCase()) && (
                            <Badge variant="outline" className="text-[10px] border-accent/30 text-accent flex-shrink-0">
                              Match
                            </Badge>
                          )}
                        </div>
                        {messagePreview && (
                          <p className="text-sm text-muted-foreground truncate">
                            {messagePreview}
                          </p>
                        )}
                        <div className="flex items-center gap-3 mt-2">
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {dateStr}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {messageCount} message{messageCount !== 1 ? 's' : ''}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {conv.messages?.filter(m => m.role === 'user').length || 0} exchange{conv.messages?.filter(m => m.role === 'user').length !== 1 ? 's' : ''}
                          </span>
                        </div>
                      </div>
                      <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-accent transition-colors flex-shrink-0 mt-1" />
                    </div>
                  </Card>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </main>
  )
}
