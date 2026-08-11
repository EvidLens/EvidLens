const plans = [
  {name: "FREE", price: "KES 0", features: ["3 Searches/mo", "1 Report/mo"]},
  {name: "SME STARTER", price: "KES 500", sub: "per Report", features: ["Pay as you go", "Full PDF Report"]},
  {name: "SME PRO", price: "KES 2,000", sub: "/month", features: ["10 Reports", "50 Searches", "Email Support"]},
  {name: "PROFESSIONAL", price: "KES 5,000", sub: "/month", features: ["30 Reports", "200 Searches", "API Access"]},
  {name: "BUSINESS", price: "KES 15,000", sub: "/month", features: ["100 Reports", "Unlimited Searches"]},
  {name: "ENTERPRISE", price: "KES 40,000+", sub: "/month", features: ["Unlimited", "Custom Data", "Dedicated Analyst"]},
]

export default function PricingPage() {
  return (
    <div className="bg-white text-gray-800">
      <div className="max-w-7xl mx-auto px-6 py-16">
        <h1 className="text-4xl font-bold text-center mb-2">Simple, Transparent Pricing</h1>
        <p className="text-center text-gray-500 mb-12">All prices incl. 16% VAT. Pay via M-Pesa</p>
        <div className="grid md:grid-cols-3 lg:grid-cols-6 gap-6">
          {plans.map(p => (
            <div key={p.name} className="border-2 border-gray-200 rounded-xl p-6 hover:border-[#2dd4bf]">
              <h3 className="font-bold text-lg">{p.name}</h3>
              <p className="text-3xl font-bold my-4">{p.price}<span className="text-sm font-normal">{p.sub}</span></p>
              <ul className="space-y-2 text-sm">{p.features.map(f => <li key={f}>✓ {f}</li>)}</ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
