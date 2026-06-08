'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Send, Brain, Loader2, History } from 'lucide-react'
import { PLATFORM } from '@/lib/api-config'
import { useAuth } from '@/hooks/useAuth'
import { toast } from 'sonner'
import axios from 'axios'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { OrderConfirmDialog } from '@/components/trading/order-confirm-dialog'

const PLATFORM_BASE = PLATFORM('/api/v1')

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  suggested_actions?: Array<{
    label: string
    action: string
    params?: Record<string, any>
  }>
}

interface SuggestedQuestion {
  icon: string
  text: string
}

const SUGGESTED_QUESTIONS: SuggestedQuestion[] = [
  { icon: '📈', text: 'What\'s your outlook on Bitcoin?' },
  { icon: '📊', text: 'How should I rebalance?' },
  { icon: '⚡', text: 'Best entry strategy now?' },
  { icon: '📚', text: 'Explain candlestick patterns' },
]

export default function ChatPage() {
  const { apiKey } = useAuth()
  const searchParams = useSearchParams()
  const router = useRouter()
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      role: 'assistant',
      content: 'Welcome to the AI trading assistant. I can help you with trading questions, portfolio analysis, and market insights. Ask me anything!',
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState('')
  const [eventSource, setEventSource] = useState<EventSource | null>(null)
  const [pendingOrderAction, setPendingOrderAction] = useState<Record<string, any> | null>(null)
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const nextIdRef = useRef(2)
  const queryClient = useQueryClient()

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Restore conversation from URL param
  useEffect(() => {
    const restoreId = searchParams.get('conversation_id')
    if (restoreId && apiKey) {
      setConversationId(restoreId)
      loadConversation(restoreId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, apiKey])

  const loadConversation = async (convId: string) => {
    try {
      const response = await axios.get(`${PLATFORM_BASE}/chat/conversation`, {
        params: { conversation_id: convId },
      })
      const conv = response.data.data
      if (conv && conv.messages && conv.messages.length > 0) {
        const restoredMessages: Message[] = [{
          id: 1,
          role: 'assistant',
          content: conv.title || 'Restored conversation',
          timestamp: new Date(conv.created_at || Date.now()),
        }]

        conv.messages.forEach((msg: any, idx: number) => {
          const isLastAssistant = msg.role === 'assistant' && idx === conv.messages.length - 1
          restoredMessages.push({
            id: restoredMessages.length + 1,
            role: msg.role,
            content: msg.content,
            timestamp: new Date(msg.timestamp || Date.now()),
            suggested_actions: isLastAssistant ? msg.suggested_actions : undefined,
          })
        })

        setMessages(restoredMessages)
        nextIdRef.current = restoredMessages.length + 1
        toast.success('Conversation restored')
      }
    } catch (e) {
      toast.error('Failed to restore conversation')
    }
  }

  // Cleanup event source on unmount
  useEffect(() => {
    return () => {
      if (eventSource) {
        eventSource.close()
      }
    }
  }, [eventSource])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    if (!apiKey) {
      toast.error('Please connect a broker to use the AI chat')
      return
    }

    const userText = input.trim()
    const userMessage: Message = {
      id: nextIdRef.current++,
      role: 'user',
      content: userText,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    // Generate conversation ID client-side if not set
    const activeConvId = conversationId || crypto.randomUUID()
    if (!conversationId) {
      setConversationId(activeConvId)
    }

    // Create placeholder assistant message for streaming
    const assistantId = nextIdRef.current++
    const assistantPlaceholder: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      suggested_actions: [],
    }
    setMessages(prev => [...prev, assistantPlaceholder])

    try {
      // Close previous event source
      if (eventSource) {
        eventSource.close()
      }

      // Build event source URL with conversation history (last 10 messages)
      const recentHistory = messages.slice(-10).map(m => ({ role: m.role, content: m.content }))
      const historyParam = encodeURIComponent(JSON.stringify(recentHistory))
      const url = `${PLATFORM_BASE}/chat/stream?` +
        `message=${encodeURIComponent(userText)}&` +
        `conversation_id=${encodeURIComponent(activeConvId)}&` +
        `apikey=${encodeURIComponent(apiKey)}&` +
        `message_history=${historyParam}`

      const es = new EventSource(url)
      setEventSource(es)
      let streamedContent = ''
      let hasContent = false

      es.onmessage = (e) => {
        if (e.data === '[DONE]') {
          es.close()
          setEventSource(null)
          setLoading(false)

          // Final update with complete content
          setMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, content: streamedContent, timestamp: new Date() }
              : m
          ))
          return
        }

        try {
          const parsed = JSON.parse(e.data)

          // Handle metadata events (conversation_id, etc.)
          if (parsed.type === 'meta') {
            if (parsed.conversation_id) {
              setConversationId(parsed.conversation_id)
            }
            return
          }

          // Handle token events
          if (parsed.token) {
            hasContent = true
            streamedContent += parsed.token
            // Update message in real-time as tokens arrive
            setMessages(prev => prev.map(m =>
              m.id === assistantId
                ? { ...m, content: streamedContent }
                : m
            ))
          }
        } catch {
          // Ignore parse errors on partial data
        }
      }

      es.onerror = () => {
        es.close()
        setEventSource(null)
        setLoading(false)

        // If we got no content, fall back to POST
        if (!hasContent) {
          fetchNonStreaming(userText, activeConvId)
        } else {
          // Partial content received — finalize what we have
          setMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, content: streamedContent || 'Connection lost. Please try again.' }
              : m
          ))
        }
      }
    } catch (error) {
      setLoading(false)
      toast.error('Failed to get AI response')
    }
  }

  const fetchNonStreaming = async (message: string, convId?: string) => {
    try {
      const response = await axios.post(`${PLATFORM_BASE}/chat`, {
        apikey: apiKey,
        message,
        conversation_id: conversationId || undefined,
        message_history: [],
        suggested_actions: true,
      })

      const data = response.data
      const assistantId = nextIdRef.current++
      const fallbackMsg: Message = {
        id: assistantId,
        role: 'assistant',
        content: data.reply || 'Sorry, I encountered an error.',
        timestamp: new Date(),
        suggested_actions: data.suggested_actions || [],
      }

      // Remove the empty placeholder and add the real message
      setMessages(prev => {
        const filtered = prev.filter(m => m.content !== '')
        return [...filtered, fallbackMsg]
      })

      if (data.conversation_id) {
        setConversationId(data.conversation_id)
      }
    } catch (error) {
      toast.error('Failed to get AI response')
    }
  }

  // ── Order execution from suggested actions ──
  const executeOrderMutation = useMutation({
    mutationFn: async (params: Record<string, any>) => {
      if (!apiKey) throw new Error('NO_BROKER')
      const response = await axios.post(
        PLATFORM('/api/v1/execute-signal'),
        {
          apikey: apiKey,
          symbol: params.symbol,
          exchange: params.exchange || 'NSE',
          decision: params.decision || 'BUY',
          confidence: params.confidence || 85,
          quantity: params.quantity || '1',
          price_type: params.price_type || 'MARKET',
          price: params.price || undefined,
          stop_loss: params.stop_loss || params.stopLoss || undefined,
          take_profit: params.take_profit || params.takeProfit || undefined,
          product: params.product || 'MIS',
        },
        { withCredentials: true }
      )
      if (response.data.status === 'error' || response.data.status === 'rejected') {
        throw new Error(response.data.message || 'Order failed')
      }
      return response.data
    },
    onSuccess: (data) => {
      toast.success(`Order placed: ${data.orderid || 'Success'}`)
      queryClient.invalidateQueries({ queryKey: ['orderbook'] })
      queryClient.invalidateQueries({ queryKey: ['positions'] })
      setConfirmDialogOpen(false)
      setPendingOrderAction(null)
    },
    onError: (error: Error) => {
      if (error.message.startsWith('NO_BROKER')) {
        toast.error('Connect a broker first', {
          action: { label: 'Setup', onClick: () => router.push('/setup') }
        })
      } else {
        toast.error(`Order failed: ${error.message}`)
      }
      setConfirmDialogOpen(false)
      setPendingOrderAction(null)
    }
  })

  // ── Symbol display helper ──
  const symbolDisplay = (symbol: string): string => symbol.split('/')[0].split(/[0-9]/)[0] || symbol

  const handleSuggestedAction = (action: any) => {
    if (action.action === 'navigate' && action.params?.path) {
      router.push(action.params.path)
    } else if (action.action === 'execute_order') {
      if (!apiKey) {
        toast.error('Connect a broker to trade', {
          action: { label: 'Setup', onClick: () => router.push('/setup') }
        })
        return
      }
      // Store the pending order and open confirmation dialog
      setPendingOrderAction(action.params || action)
      setConfirmDialogOpen(true)
    }
  }

  // Build order details for the confirmation dialog from suggested action params
  const buildOrderDetails = () => {
    if (!pendingOrderAction) return null
    const p = pendingOrderAction
    const decision = (p.decision || 'BUY').toLowerCase()
    const sym = p.symbol || ''
    return {
      action: decision as 'buy' | 'sell',
      symbol: sym,
      displaySymbol: symbolDisplay(sym),
      exchange: p.exchange || 'NSE',
      amount: String(p.quantity || '1'),
      price: p.price ? parseFloat(p.price) : null,
      orderType: (p.price_type || 'MARKET').toLowerCase() as 'market' | 'limit',
      stopLoss: p.stop_loss || p.stopLoss || '',
      takeProfit: p.take_profit || p.takeProfit || '',
      leverage: p.leverage || 1,
    }
  }

  const handleConfirmOrder = () => {
    if (pendingOrderAction) {
      executeOrderMutation.mutate(pendingOrderAction)
    }
  }



  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col h-screen">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <Brain className="w-6 h-6 text-accent" />
            <h1 className="text-3xl font-bold">Expert Trading Assistant</h1>
          </div>
          <p className="text-muted-foreground">AI-powered trading insights with real-time portfolio context</p>
        </div>

        {/* Chat Container */}
        <Card className="flex-1 p-6 border-border flex flex-col overflow-hidden mb-6">
          {/* Messages */}
          <div className="overflow-y-auto flex-1 space-y-4 mb-6">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-3 rounded-lg ${
                    message.role === 'user'
                      ? 'bg-accent text-accent-foreground rounded-br-none'
                      : 'bg-card border border-border rounded-bl-none'
                  }`}
                >
                  <p className="text-sm break-words">{message.content}</p>
                  <p className={`text-xs mt-2 ${
                    message.role === 'user' ? 'opacity-70' : 'text-muted-foreground'
                  }`}>
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                  {message.suggested_actions && message.suggested_actions.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {message.suggested_actions.map((action, idx) => (
                        <Button
                          key={idx}
                          variant="outline"
                          size="sm"
                          onClick={() => handleSuggestedAction(action)}
                          className="text-xs border-accent/30 hover:bg-accent/10"
                        >
                          {action.label}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-card border border-border px-4 py-3 rounded-lg rounded-bl-none">
                  <Loader2 className="w-4 h-4 animate-spin text-accent" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Form */}
          <form onSubmit={handleSendMessage} className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about trading, markets, or your portfolio..."
              disabled={loading}
              className="bg-card/50 border-border focus:border-accent/50 focus:ring-1 focus:ring-accent/50"
            />
            <Button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              <span className="hidden sm:inline">{loading ? 'Sending...' : 'Send'}</span>
            </Button>
          </form>
        </Card>

        {/* Suggested Questions */}
        {messages.length === 1 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {SUGGESTED_QUESTIONS.map((q, i) => (
              <button
                key={i}
                onClick={() => setInput(q.text)}
                className="p-4 rounded-lg border border-border bg-card/50 hover:border-accent/30 hover:bg-card/70 transition-all text-left group"
              >
                <div className="text-lg mb-2 group-hover:text-accent transition-colors">
                  {q.icon}
                </div>
                <p className="text-sm font-medium">{q.text}</p>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Order Confirmation Dialog */}
      {pendingOrderAction && buildOrderDetails() && (
        <OrderConfirmDialog
          open={confirmDialogOpen}
          onOpenChange={(val) => {
            setConfirmDialogOpen(val)
            if (!val) setPendingOrderAction(null)
          }}
          orderDetails={buildOrderDetails()!}
          onConfirm={handleConfirmOrder}
          isPending={executeOrderMutation.isPending}
        />
      )}
    </main>
  )
}
