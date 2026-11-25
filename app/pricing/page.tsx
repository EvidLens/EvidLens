"use client";

import { useState } from "react";
import Link from "next/link";

type Billing = "monthly" | "yearly";

const PLANS = [
  {
    name: "FREE",
    tagline: "Try EvidLens",
    monthly: 0,
    yearly: 0,
    cta: "Start Free",
    href: "/signup",
    featured: false,
    features: [
      "5 free credits on signup",
      "5 searches",
      "1 report",
      "All 6 Lens tools - trial",
      "M-Pesa pay-as-you-go",
    ],
  },
  {
    name: "BASIC",
    tagline: "For one hustle",
    monthly: 500,
    yearly: 5000,
    cta: "Choose BASIC",
    href: "/billing?plan=basic",
    featured: false,
    features: [
      "10 analyses / month",
      "5 reports / month",
      "All 6 Lens tools",
      "PDF downloads",
      "M-Pesa checkout",
    ],
  },
  {
    name: "PROFESSIONAL",
    tagline: "Most popular",
    monthly: 1500,
    yearly: 15000,
    cta: "Choose PROFESSIONAL",
    href: "/billing?plan=professional",
    featured: true,
    features: [
      "100 analyses / month",
      "30 reports / month",
      "All 6 Lens tools",
      "Priority support",
      "Competitor tracking",
      "PDF + Excel downloads",
    ],
  },
  {
    name: "ENTERPRISE",
    tagline: "For teams & counties",
    monthly: 5000,
    yearly: 50000,
    cta: "Choose ENTERPRISE",
    href: "/billing?plan=enterprise",
    featured: false,
    features: [
      "Unlimited analyses",
      "Unlimited reports",
      "All 6 Lens tools",
      "API access",
      "Team seats - up to 5",
      "Dedicated support",
    ],
  },
];

const CREDIT_PACKAGES = [
  { credits: 5, price: 500, note: "KES 100 / credit" },
  { credits: 20, price: 1800, note: "KES 90 / credit - Save KES 200" },
  { credits: 50, price: 4000, note: "KES 80 / credit - Save KES 1,000" },
];

function formatKES(n: number) {
  return "KES " + n.toLocaleString("en-KE");
}

export default function PricingPage() {
  const [billing, setBilling] = useState<Billing>("monthly");

  return (
    <main className="bg-white text-gray-800">
      <div className="max-w-7xl mx-auto px-6 py-16">
        <h1 className="text-4xl font-bold text-center mb-2">Simple, Transparent Pricing</h1>
        <p className="text-center text-gray-500 mb-4">
          Pay via M-Pesa. No card required. Cancel anytime.
        </p>
        <p className="text-center text-sm text-gray-500 mb-8">
          Prices include 16% VAT. 1 credit = 1 analysis. Credits never expire.
        </p>

        <div className="flex justify-center mb-10">
          <div className="bg-gray-100 rounded-full p-1 flex">
            <button
              onClick={() => setBilling("monthly")}
              className={`px-5 py-2 rounded-full text-sm font-bold ${billing === "monthly" ? "bg-[#0A1F44] text-white" : "text-gray-600"}`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBilling("yearly")}
              className={`px-5 py-2 rounded-full text-sm font-bold ${billing === "yearly" ? "bg-[#0A1F44] text-white" : "text-gray-600"}`}
            >
              Yearly - 2 months free
            </button>
          </div>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {PLANS.map((p) => {
            const price = billing === "monthly" ? p.monthly : p.yearly;
            const perMonth = billing === "yearly" && p.yearly > 0 ? Math.round(p.yearly / 12) : p.monthly;
            return (
              <div
                key={p.name}
                className={`border-2 rounded-xl p-6 flex flex-col ${p.featured ? "border-[#14B8A6] shadow-lg relative" : "border-gray-200 hover:border-[#2dd4bf]"}`}
              >
                {p.featured && (
                  <span className="absolute -top-3 left-6 bg-[#14B8A6] text-white text-xs font-bold px-3 py-1 rounded-full">
                    MOST POPULAR
                  </span>
                )}
                <h3 className="font-bold text-lg">{p.name}</h3>
                <p className="text-sm text-gray-500">{p.tagline}</p>
                <p className="text-3xl font-bold my-4">
                  {formatKES(price)}
                  <span className="text-sm font-normal text-gray-500">
                    {price === 0 ? " forever" : billing === "monthly" ? " /month" : " /year"}
                  </span>
                </p>
                {billing === "yearly" && p.yearly > 0 && (
                  <p className="text-sm text-teal-700 font-semibold -mt-2 mb-2">
                    {formatKES(perMonth)} /month - you save {formatKES(p.monthly * 12 - p.yearly)}
                  </p>
                )}
                <ul className="space-y-2 text-sm flex-1">
                  {p.features.map((f) => (
                    <li key={f}>✓ {f}</li>
                  ))}
                </ul>
                <Link
                  href={p.href}
                  className={`mt-6 text-center py-3 rounded-lg font-bold ${p.featured ? "bg-[#14B8A6] text-white" : "bg-[#0A1F44] text-white"}`}
                >
                  {p.cta}
                </Link>
              </div>
            );
          })}
        </div>

        <div className="mt-16">
          <h2 className="text-2xl font-bold text-center mb-2">Or buy credits - pay as you go</h2>
          <p className="text-center text-gray-500 text-sm mb-6">
            No subscription. Use credits for any analysis. M-Pesa STK Push.
          </p>
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {CREDIT_PACKAGES.map((pkg) => (
              <div key={pkg.credits} className="border-2 border-gray-200 rounded-xl p-6 text-center hover:border-[#2dd4bf]">
                <p className="text-3xl font-bold">{pkg.credits} Credits</p>
                <p className="text-2xl font-bold my-3">{formatKES(pkg.price)}</p>
                <p className="text-sm text-gray-500 mb-4">{pkg.note}</p>
                <Link href={`/wallet?pack=${pkg.credits}`} className="inline-block bg-[#0A1F44] text-white px-6 py-2 rounded-lg font-bold">
                  Buy {pkg.credits} Credits
                </Link>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 text-center text-sm text-gray-500">
          <p>All plans include Kenya data: 47 counties, KNBS, KEPHIS, and market prices.</p>
          <p className="mt-2">
            Questions? <Link href="/contact" className="text-teal-700 underline">Contact us</Link> or see{" "}
            <Link href="/privacy" className="text-teal-700 underline">Privacy Policy</Link>
          </p>
        </div>
      </div>
    </main>
  );
}
