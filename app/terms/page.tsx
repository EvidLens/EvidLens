export default function TermsPage() {
  return (
    <div className="bg-white text-gray-800">
      <div className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-4xl font-bold mb-2">EvidLens Terms of Service</h1>
        <p className="text-sm text-gray-500 mb-10">Last Updated: April 2026</p>
        
        <div className="prose prose-lg max-w-none space-y-6">
          <section><h2 className="text-2xl font-semibold">1. Service Description</h2><p>Informational only. Not financial or legal advice.</p></section>
          <section><h2 className="text-2xl font-semibold">2. Payments & Refunds</h2><p>All payments via M-Pesa. Reports KES 500 are non-refundable once generated. Subscriptions auto-renew. Cancel anytime.</p></section>
          <section><h2 className="text-2xl font-semibold">3. Limitation of Liability</h2><p>Max liability is amount paid in last 30 days.</p></section>
          <section><h2 className="text-2xl font-semibold">4. Governing Law</h2><p>Laws of the Republic of Kenya.</p></section>
        </div>
      </div>
    </div>
  )
}
