export default function AboutPage() {
  return (
    <div className="bg-white text-gray-800">
      <div className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-4xl font-bold mb-6">About EvidLens</h1>
        <p className="text-xl mb-8"><b>EvidLens</b> is Decision Intelligence for Kenyan SMEs.</p>
        <div className="prose prose-lg max-w-none space-y-6">
          <section><h2 className="text-2xl font-semibold">Our Mission</h2><p>Reduce the 80% SME failure rate in Kenya by giving entrepreneurs data BEFORE they invest capital.</p></section>
          <section><h2 className="text-2xl font-semibold">Who We Serve</h2><p>Retailers, Wholesalers, Manufacturers, and Service providers across all 47 counties in Kenya.</p></section>
          <section><h2 className="text-2xl font-semibold">Founded</h2><p>2025 | Nyeri, Kenya | Built for Kenya, by Kenyans</p></section>
        </div>
      </div>
    </div>
  )
}
