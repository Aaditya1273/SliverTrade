export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl font-bold mb-8">Privacy Policy</h1>
        
        <div className="prose prose-invert max-w-none space-y-6">
          <section>
            <h2 className="text-xl font-semibold mb-3">1. Data Collected</h2>
            <p className="text-muted-foreground">
              We collect the following data:
              <br />• Email address (for account and communication)
              <br />• Usage data (pages visited, features used)
              <br />• Trading activity (signals viewed, orders placed)
              <br />• IP address (for security and rate limiting)
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">2. Broker Credentials</h2>
            <p className="text-muted-foreground">
              Your broker API keys and credentials are stored encrypted at rest using industry-standard encryption (AES-256). 
              We do NOT share your broker credentials with any third party. 
              Credentials are used solely to execute trades on your behalf when you authorize it.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">3. LLM Data (AI Chat)</h2>
            <p className="text-muted-foreground">
              When you use the AI Chat feature, your messages are sent to OpenAI's GPT-4o API to generate responses. 
              OpenAI may process your messages as described in their privacy policy. 
              We do NOT use your chat messages to train our own models.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">4. Data Retention</h2>
            <p className="text-muted-foreground">
              Your data is retained as follows:
              <br />• Account data: Until you delete your account
              <br />• Trading history: 7 years (regulatory compliance)
              <br />• Chat history: Until you delete it or your account
              <br />• Analytics data: 90 days
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">5. Your Rights (DPDP Act 2023)</h2>
            <p className="text-muted-foreground">
              Under India's Digital Personal Data Protection Act 2023, you have the right to:
              <br />• Access all data we hold about you
              <br />• Correct inaccurate data
              <br />• Delete your account and all associated data
              <br />• Withdraw consent for data processing
              <br />• Data portability (export your data)
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">6. Third-Party Services</h2>
            <p className="text-muted-foreground">
              We use the following third-party services:
              <br />• <strong>Stripe:</strong> Payment processing (billing data)
              <br />• <strong>OpenAI:</strong> AI Chat responses
              <br />• <strong>Broker APIs:</strong> Trade execution (credentials encrypted)
              <br />Each service has its own privacy policy which you should review.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">7. Cookies</h2>
            <p className="text-muted-foreground">
              We use cookies for:
              <br />• Session authentication (required)
              <br />• Analytics (optional, with your consent)
              <br />• Preference storage (required)
              <br />You can manage cookie preferences through our cookie consent banner.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">8. Data Security</h2>
            <p className="text-muted-foreground">
              We implement industry-standard security measures:
              <br />• Encryption at rest (AES-256)
              <br />• Encryption in transit (TLS 1.2+)
              <br />• Regular security audits
              <br />• Access controls and authentication
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">9. Contact</h2>
            <p className="text-muted-foreground">
              For privacy-related questions or to exercise your rights, contact us at privacy@silvertrade.ai
            </p>
          </section>

          <section className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <p className="text-sm text-amber-600 dark:text-amber-400">
              <strong>DPDP Act 2023 Compliance:</strong> This privacy policy is designed to comply with India's 
              Digital Personal Data Protection Act 2023. You have the right to access, correct, and delete your data.
            </p>
          </section>
        </div>

        <p className="text-sm text-muted-foreground mt-8">
          Last updated: {new Date().toLocaleDateString()}
        </p>
      </div>
    </div>
  )
}
