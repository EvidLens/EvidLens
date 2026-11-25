import Link from "next/link";

const TOOLS = [
  {
    name: "Demand Lens",
    desc: "Is there real demand for this product in this county, right now?",
  },
  {
    name: "Competitive Lens",
    desc: "Who else is selling it, at what price, and where is the gap?",
  },
  {
    name: "Risk Sentinel",
    desc: "What could go wrong - price swings, regulation, supply shocks?",
  },
  {
    name: "Market Intelligence",
    desc: "Live market prices, county trends, and KNBS / KEPHIS data in one place.",
  },
  {
    name: "Policy Watch",
    desc: "New county and national policies that affect your business, explained simply.",
  },
  {
    name: "Report Builder",
    desc: "A full PDF business report you can take to a SACCO, bank, or partner.",
  },
];

const STEPS = [
  {
    title: "1. Tell us your idea",
    desc: "Product, county, subcounty, and budget. Takes 2 minutes.",
  },
  {
    title: "2. EvidLens checks real data",
    desc: "Market prices, county demand, competitors, and policy - not guesswork.",
  },
  {
    title: "3. Get a clear answer",
    desc: "Go, No-Go, or Pivot - with numbers, risks, and next steps.",
  },
];

const VALUES = [
  {
    title: "Kenya first",
    desc: "47 counties, local markets, M-Pesa, and prices in KES. Not a copy of a US tool.",
  },
  {
    title: "Evidence over hype",
    desc: "If the data says No, we say No. A saved KES 50,000 is worth more than a false Yes.",
  },
  {
    title: "Affordable",
    desc: "Start free. Pay KES 500 for credits, or KES 500/month for BASIC. No card required.",
  },
  {
    title: "Simple language",
    desc: "No jargon. Every report is written so a first-time founder can act on it.",
  },
];

export default function AboutPage() {
  return (
    <main className="bg-white text-gray-800">
      <div className="max-w-4xl mx-auto px-6 py-16">
        <p className="text-sm font-semibold text-teal-600 tracking-wide uppercase mb-2">
          Nyeri, Kenya - Founded 2025
        </p>
        <h1 className="text-4xl font-bold mb-6">About EvidLens</h1>
        <p className="text-xl mb-4 leading-relaxed">
          <b>EvidLens</b> is Decision Intelligence for Kenyan SMEs.
        </p>
        <p className="text-gray-600 leading-relaxed mb-10">
          Too many good businesses fail not because the founder was lazy, but because
          they invested before they had data. EvidLens gives you that data first -
          demand, prices, competitors, and risks - before you spend capital.
        </p>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-3">Our Mission</h2>
          <p className="leading-relaxed">
            Reduce SME failure in Kenya by giving entrepreneurs data BEFORE they
            invest capital. A KES 500 analysis that stops a KES 200,000 mistake is
            the best return a founder can get.
          </p>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-3">Who We Serve</h2>
          <p className="leading-relaxed mb-4">
            Retailers, wholesalers, manufacturers, agribusinesses, and service
            providers across all 47 counties in Kenya - from a mama mboga testing
            a second stall in Karatina, to a wholesaler choosing between Nyeri and
            Nairobi.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="border rounded-xl p-4">
              <p className="text-2xl font-bold">47</p>
              <p className="text-sm text-gray-500">Counties covered</p>
            </div>
            <div className="border rounded-xl p-4">
              <p className="text-2xl font-bold">6</p>
              <p className="text-sm text-gray-500">Lens tools</p>
            </div>
            <div className="border rounded-xl p-4">
              <p className="text-2xl font-bold">KES 500</p>
              <p className="text-sm text-gray-500">Starting price</p>
            </div>
            <div className="border rounded-xl p-4">
              <p className="text-2xl font-bold">2 min</p>
              <p className="text-sm text-gray-500">To first analysis</p>
            </div>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">What EvidLens Does</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            {TOOLS.map((t) => (
              <div key={t.name} className="border rounded-xl p-5">
                <h3 className="font-bold mb-1">{t.name}</h3>
                <p className="text-sm text-gray-600">{t.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">How It Works</h2>
          <div className="space-y-4">
            {STEPS.map((s) => (
              <div key={s.title} className="border rounded-xl p-5">
                <h3 className="font-bold mb-1">{s.title}</h3>
                <p className="text-sm text-gray-600">{s.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">What We Believe</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            {VALUES.map((v) => (
              <div key={v.title} className="border rounded-xl p-5">
                <h3 className="font-bold mb-1">{v.title}</h3>
                <p className="text-sm text-gray-600">{v.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-3">Founded</h2>
          <p className="leading-relaxed">
            2025 | Nyeri, Kenya | Built for Kenya, by Kenyans.
          </p>
          <p className="text-gray-600 leading-relaxed mt-2">
            EvidLens started in Nyeri because that is where the gap is clearest:
            smart founders with no access to the data big companies use. We are
            building the tool we wish every Kenyan founder had before their first
            stock purchase.
          </p>
        </section>

        <div className="border-t pt-8 flex flex-wrap gap-4">
          <Link href="/signup" className="bg-[#0A1F44] text-white px-6 py-3 rounded-lg font-bold">
            Try EvidLens Free
          </Link>
          <Link href="/pricing" className="border px-6 py-3 rounded-lg font-bold">
            See Pricing
          </Link>
          <Link href="/contact" className="border px-6 py-3 rounded-lg font-bold">
            Contact Us
          </Link>
        </div>
      </div>
    </main>
  );
}
