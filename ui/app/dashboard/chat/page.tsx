'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Send, Brain } from 'lucide-react'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      role: 'assistant',
      content: 'Welcome to the AI trading assistant. I can help explain trading concepts and review signal reasoning from our technical analysis engine. Note: This is a demo interface — LLM integration is planned for Phase 6.',
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    // Add user message
    const userMessage: Message = {
      id: messages.length + 1,
      role: 'user',
      content: input,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    // Demo response — real LLM integration planned for Phase 6
    setTimeout(() => {
      const assistantMessage: Message = {
        id: messages.length + 2,
        role: 'assistant',
        content: 'Thanks for your question! The AI chat assistant is currently in demo mode. Full LLM integration with real-time market data access, portfolio analysis, and natural language strategy discussions is planned for a future update. In the meantime, check the AI Signals panel for generated trading signals with confidence scores and reasoning.',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, assistantMessage])
      setLoading(false)
    }, 1500)
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
          <p className="text-muted-foreground">Demo assistant — LLM integration coming in a future update</p>
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
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-card border border-border px-4 py-3 rounded-lg rounded-bl-none">
                  <div className="flex gap-2">
                    <div className="w-2 h-2 bg-accent rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-accent rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                    <div className="w-2 h-2 bg-accent rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
                  </div>
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
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Send</span>
            </Button>
          </form>
        </Card>

        {/* Suggested Questions */}
        {messages.length === 1 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { icon: 'trending', text: 'What\'s your outlook on Bitcoin?' },
              { icon: 'chart', text: 'How should I rebalance?' },
              { icon: 'zap', text: 'Best entry strategy now?' },
              { icon: 'book', text: 'Explain candlestick patterns' },
            ].map((q, i) => (
              <button
                key={i}
                onClick={() => setInput(q.text)}
                className="p-4 rounded-lg border border-border bg-card/50 hover:border-accent/30 hover:bg-card/70 transition-all text-left group"
              >
                <div className="text-lg mb-2 group-hover:text-accent transition-colors">
                  {q.icon === 'trending' && '📈'}
                  {q.icon === 'chart' && '📊'}
                  {q.icon === 'zap' && '⚡'}
                  {q.icon === 'book' && '📚'}
                </div>
                <p className="text-sm font-medium">{q.text}</p>
              </button>
            ))}
          </div>
        )}
      </div>
    </main>
  )
}
