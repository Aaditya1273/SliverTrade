import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { ArrowRight, TrendingUp, Brain, Zap, Lock, BarChart3 } from 'lucide-react'

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      {/* Navigation */}
      <nav className="fixed top-0 w-full border-b border-border/50 backdrop-blur-md z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="text-xl font-bold tracking-tight">SilverTrade</div>
          <div className="hidden md:flex gap-8 items-center">
            <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Features</a>
            <a href="#how-it-works" className="text-sm text-muted-foreground hover:text-foreground transition-colors">How It Works</a>
            <a href="#pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Pricing</a>
            <Button variant="default" size="sm" asChild>
              <Link href="/login">Sign In</Link>
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-block mb-6 px-4 py-2 rounded-full bg-secondary/30 border border-accent/20">
            <span className="text-xs font-semibold text-accent uppercase tracking-wider">AI-Powered Trading Intelligence</span>
          </div>
          
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold mb-6 tracking-tight">
            Make Confident
            <span className="block text-accent">Crypto Decisions</span>
          </h1>
          
          <p className="text-lg sm:text-xl text-muted-foreground mb-8 max-w-2xl mx-auto leading-relaxed">
            SilverTrade AI combines technical indicators (RSI, MACD, EMA, Bollinger Bands) to generate clear trading signals. Trade with conviction, not emotion.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <Button size="lg" className="gap-2" asChild>
              <Link href="/dashboard">
                Start Trading Free <ArrowRight className="w-5 h-5" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="#demo">Watch Demo</Link>
            </Button>
          </div>

          {/* Honest Status */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 pt-12 border-t border-border">
            <div>
              <div className="text-3xl font-bold text-accent mb-2">Beta</div>
              <p className="text-sm text-muted-foreground">Early Access Program</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-accent mb-2">7</div>
              <p className="text-sm text-muted-foreground">Technical Indicators Analyzed</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-accent mb-2">30+</div>
              <p className="text-sm text-muted-foreground">Supported Broker Exchanges</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4 sm:px-6 lg:px-8 border-t border-border">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold mb-12 text-center">Why SilverTrade Traders Win</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="p-6 rounded-lg border border-border bg-card/50 hover:border-accent/30 transition-colors group">
              <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center mb-4 group-hover:bg-accent/20 transition-colors">
                <Brain className="w-6 h-6 text-accent" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Technical Analysis Engine</h3>
              <p className="text-sm text-muted-foreground">Multi-indicator engine combining RSI, MACD, EMA, and Bollinger Bands into clear BUY/SELL/HOLD signals</p>
            </div>

            {/* Feature 2 */}
            <div className="p-6 rounded-lg border border-border bg-card/50 hover:border-accent/30 transition-colors group">
              <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center mb-4 group-hover:bg-accent/20 transition-colors">
                <Zap className="w-6 h-6 text-accent" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Real-Time Signals</h3>
              <p className="text-sm text-muted-foreground">Live signal generation from exchange market data with confidence scoring and reasoning</p>
            </div>

            {/* Feature 3 */}
            <div className="p-6 rounded-lg border border-border bg-card/50 hover:border-accent/30 transition-colors group">
              <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center mb-4 group-hover:bg-accent/20 transition-colors">
                <TrendingUp className="w-6 h-6 text-accent" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Broker Integration</h3>
              <p className="text-sm text-muted-foreground">Connect 30+ brokers including Zerodha, Angel, Dhan, Binance, and more via secure API</p>
            </div>

            {/* Feature 4 */}
            <div className="p-6 rounded-lg border border-border bg-card/50 hover:border-accent/30 transition-colors group">
              <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center mb-4 group-hover:bg-accent/20 transition-colors">
                <Lock className="w-6 h-6 text-accent" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Secure Authentication</h3>
              <p className="text-sm text-muted-foreground">Session-based auth with CSRF protection, rate limiting, and encrypted broker token storage</p>
            </div>

            {/* Feature 5 */}
            <div className="p-6 rounded-lg border border-border bg-card/50 hover:border-accent/30 transition-colors group">
              <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center mb-4 group-hover:bg-accent/20 transition-colors">
                <BarChart3 className="w-6 h-6 text-accent" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Options Analytics</h3>
              <p className="text-sm text-muted-foreground">Greeks, IV smile, volatility surface, OI tracker, and GEX analysis for advanced traders</p>
            </div>

            {/* Feature 6 */}
            <div className="p-6 rounded-lg border border-border bg-card/50 hover:border-accent/30 transition-colors group">
              <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center mb-4 group-hover:bg-accent/20 transition-colors">
                <Brain className="w-6 h-6 text-accent" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Signal History</h3>
              <p className="text-sm text-muted-foreground">Track every generated signal with confidence scores, reasoning, and price data</p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-20 px-4 sm:px-6 lg:px-8 border-t border-border bg-card/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-4xl font-bold mb-12 text-center">Three Steps to Profitable Trading</h2>
          
          <div className="space-y-8">
            {[
              {
                num: "01",
                title: "Connect Your Exchange",
                desc: "Link your favorite exchange securely. Read-only access—we never hold your keys."
              },
              {
                num: "02",
                title: "Receive Trading Signals",
                desc: "Our technical analysis engine processes market data through 7 indicators and generates clear BUY/SELL/HOLD decisions."
              },
              {
                num: "03",
                title: "Execute & Profit",
                desc: "Execute trades with a single click or enable auto-trading. Track your performance and optimize constantly."
              }
            ].map((step) => (
              <div key={step.num} className="flex gap-6 items-start">
                <div className="text-5xl font-bold text-muted-foreground/30">{step.num}</div>
                <div className="flex-1 pt-2">
                  <h3 className="text-xl font-semibold mb-2">{step.title}</h3>
                  <p className="text-muted-foreground">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-4xl font-bold mb-6">Ready to Trade Smarter?</h2>
          <p className="text-lg text-muted-foreground mb-8">
            Start making data-driven trading decisions with SilverTrade AI
          </p>
          <Button size="lg" className="gap-2" asChild>
            <Link href="/dashboard">
              Get Started Free <ArrowRight className="w-5 h-5" />
            </Link>
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-12 px-4 sm:px-6 lg:px-8 bg-card/30">
        <div className="max-w-6xl mx-auto grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-8 mb-8">
          <div>
            <h4 className="font-semibold mb-4">Product</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><a href="#" className="hover:text-foreground transition-colors">Features</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Pricing</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Security</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-4">Resources</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><a href="#" className="hover:text-foreground transition-colors">Blog</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Guides</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">API Docs</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-4">Company</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><a href="#" className="hover:text-foreground transition-colors">About</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Careers</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Contact</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-4">Legal</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><a href="#" className="hover:text-foreground transition-colors">Privacy</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Terms</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Disclosures</a></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-border pt-8 flex flex-col sm:flex-row justify-between items-center text-sm text-muted-foreground">
          <p>&copy; 2026 SilverTrade AI. All rights reserved.</p>
          <p>Built for traders. Powered by AI.</p>
        </div>
      </footer>
    </main>
  )
}
