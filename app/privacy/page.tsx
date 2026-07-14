export default function PrivacyPage() {
  return (
    <div className="bg-white text-gray-800">
      <div className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-4xl font-bold mb-2">EvidLens Privacy Policy</h1>
        <p className="text-sm text-gray-500 mb-10">Last Updated: April 2026</p>
        
        <div className="prose prose-lg max-w-none space-y-6">
          <section>
            <h2 className="text-2xl font-semibold">1. Who We Are</h2>
            <p>EvidLens Ltd is a Kenyan company based in Kenya. We provide AI-powered market intelligence for SMEs. Data Protection Officer: dpo@evidlens.co.ke</p>
          </section>
          <section>
            <h2 className="text-2xl font-semibold">2. What Data We Collect</h2>
            <ul>
              <li><b>Account Information</b>: Name, email address, phone number</li>
              <li><b>Payment Information</b>: M-Pesa phone number, CheckoutRequestID, M-Pesa Receipt Number. We NEVER store your M-Pesa PIN.</li>
              <li><b>Usage Data</b>: Business sector, county, reports downloaded, AI questions</li>
              <li><b>Technical Data</b>: IP address, device type, for security</li>
            </ul>
          </section>
          <section>
            <h2 className="text-2xl font-semibold">3. How We Use Your Data</h2>
            <p>To generate reports, process M-Pesa payments, manage subscriptions, improve AI, and send receipts.</p>
          </section>
          <section>
            <h2 className="text-2xl font-semibold">4. Your Rights - DPA 2019</h2>
            <p>You can Access, Correct, or Delete your data. Email dpo@evidlens.com. Response in 14 days.</p>
          </section>
        </div>
      </div>
    </div>
  )
}
