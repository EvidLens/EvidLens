import Link from "next/link";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "Pricing", href: "/pricing" },
      { label: "Demand Lens", href: "/tools/demand" },
      { label: "Competitive Lens", href: "/tools/competitive" },
      { label: "Risk Sentinel", href: "/tools/risk" },
      { label: "Policy Watch", href: "/tools/policy" },
      { label: "Report Builder", href: "/tools/reports" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "/about" },
      { label: "Contact Us", href: "/contact" },
      { label: "Pricing", href: "/pricing" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy", href: "/privacy" },
      { label: "Terms of Service", href: "/terms" },
    ],
  },
  {
    title: "Support",
    links: [
      { label: "Contact Us", href: "/contact" },
      { label: "Pricing", href: "/pricing" },
      { label: "Login", href: "/login" },
      { label: "Sign Up Free", href: "/signup" },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="bg-[#0F1A2E] text-white pt-12 pb-6">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8">
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="text-xl font-bold">
              Evid<span className="text-teal-400">Lens</span>
            </Link>
            <p className="text-sm text-gray-300 mt-3 leading-relaxed">
              Decision Intelligence for Kenyan SMEs. Data before you invest.
            </p>
            <p className="text-sm text-gray-300 mt-4">
              Nyeri, Kenya
            </p>
            <p className="text-sm text-gray-300 mt-1">
              <a href="mailto:support@evidlens.co.ke" className="hover:text-white">
                support@evidlens.co.ke
              </a>
            </p>
            <p className="text-sm text-gray-300 mt-1">
              DPO:{" "}
              <a href="mailto:dpo@evidlens.co.ke" className="hover:text-white">
                dpo@evidlens.co.ke
              </a>
            </p>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.title}>
              <h3 className="text-teal-400 font-semibold mb-4">{col.title}</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                {col.links.map((link) => (
                  <li key={link.label + link.href}>
                    <Link href={link.href} className="hover:text-white">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-gray-700 mt-8 pt-6 flex flex-col sm:flex-row justify-between gap-2 text-center sm:text-left text-xs text-gray-400">
          <p>© 2026 EvidLens Ltd. Decision Intelligence for Kenyan SMEs.</p>
          <p>Pay via M-Pesa. Prices include 16% VAT.</p>
        </div>
      </div>
    </footer>
  );
}
