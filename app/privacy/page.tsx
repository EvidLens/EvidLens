import Link from "next/link";

const SECTIONS = [
  {
    id: "who-we-are",
    title: "1. Who We Are",
    body: "EvidLens Ltd is a Kenyan company providing AI-powered market intelligence for SMEs in Kenya. Our Data Protection Officer (DPO) is reachable at dpo@evidlens.co.ke. This policy explains what we collect, why, how long we keep it, and your rights under the Kenya Data Protection Act, 2019 (DPA 2019).",
  },
  {
    id: "data-we-collect",
    title: "2. What Data We Collect",
    list: [
      "Account Information: Name, email address, phone number, county, sector, subcounty.",
      "Payment Information: M-Pesa phone number, CheckoutRequestID, MerchantRequestID, M-Pesa Receipt Number, amount, and payment status. We NEVER store your M-Pesa PIN, and we never ask for it.",
      "Usage Data: Business sector, county, reports generated and downloaded, AI questions, credits balance, plan, and subscription status.",
      "Technical Data: IP address, device type, browser, and login timestamps, used for security and fraud prevention.",
      "Support Data: Messages you send to support@evidlens.co.ke or dpo@evidlens.co.ke, and your replies to them.",
    ],
  },
  {
    id: "how-we-use",
    title: "3. How We Use Your Data",
    list: [
      "To create your account, verify your email, and keep you logged in.",
      "To generate reports, analyses, and AI answers you request.",
      "To process M-Pesa payments, issue receipts, and manage subscriptions and credits.",
      "To prevent fraud, abuse, and unauthorized access, and to enforce our Terms.",
      "To improve EvidLens, fix bugs, and measure which features are used. We do not sell your personal data.",
      "To send you receipts, payment confirmations, security alerts, and service updates. Marketing messages are only sent if you opt in, and you can opt out at any time.",
    ],
  },
  {
    id: "lawful-basis",
    title: "4. Lawful Basis - DPA 2019",
    body: "We process your data because: (a) it is necessary to perform our contract with you - to deliver reports and paid credits; (b) we have a legal obligation - to keep payment and tax records; (c) we have a legitimate interest - to secure the service and prevent fraud; and (d) you consented - for optional marketing and analytics cookies. You may withdraw consent at any time.",
  },
  {
    id: "sharing",
    title: "5. Who We Share Data With",
    list: [
      "Safaricom Daraja / M-Pesa: To initiate and confirm STK Push payments. They receive your phone number, amount, and CheckoutRequestID.",
      "Groq (AI provider): To generate AI summaries. We send your prompt and business context, not your M-Pesa PIN or full payment details.",
      "Hosting and analytics providers: To host the app, store backups, and measure uptime. They process data only on our instructions.",
      "Law enforcement / regulators: Only when required by Kenyan law or a valid court order, and only the minimum data required.",
    ],
    body: "We do not sell your personal data to data brokers, advertisers, or third parties.",
  },
  {
    id: "cookies",
    title: "6. Cookies and Similar Technologies",
    list: [
      "Essential cookies: user_id session cookie to keep you logged in, and oauth_state to secure Google / Microsoft login. These are required for the service to work.",
      "Preference cookies: Language and last-selected county / sector, to remember your choices.",
      "Analytics cookies: Anonymous usage counts to improve the product. You can block these in your browser without breaking the core service.",
    ],
  },
  {
    id: "retention",
    title: "7. How Long We Keep Data",
    list: [
      "Account data: While your account is active, plus 12 months after you delete it, to resolve disputes and comply with tax law.",
      "Payment records: 5 years, as required by Kenyan tax and accounting law. Payment records are kept even after account deletion, but without your phone number where possible.",
      "Reports and AI history: Until you delete them, or 12 months after your last login, whichever is earlier.",
      "Security logs: 90 days, then deleted or anonymized.",
    ],
  },
  {
    id: "security",
    title: "8. How We Protect Your Data",
    body: "We use HTTPS on all pages, hashed passwords (bcrypt), HttpOnly session cookies, and access controls that limit who can view your reports. No system is 100% secure. If you suspect unauthorized access to your account, change your password and email support@evidlens.co.ke immediately. Never share your M-Pesa PIN, password, or OTP with anyone claiming to be EvidLens.",
  },
  {
    id: "transfers",
    title: "9. International Transfers",
    body: "Some processors (for example Groq and our hosting provider) may store or process data outside Kenya. Where that happens, we rely on safeguards required by DPA 2019, including contractual protections and processing only the minimum data needed for that service.",
  },
  {
    id: "rights",
    title: "10. Your Rights - DPA 2019",
    list: [
      "Access: Ask for a copy of the personal data we hold about you.",
      "Correction: Ask us to fix inaccurate name, email, phone, county, or sector.",
      "Deletion: Ask us to delete your account and personal data, subject to payment-record retention above.",
      "Objection and restriction: Ask us to stop marketing or limit processing.",
      "Portability: Ask for your reports and account data in a usable format.",
      "Complaint: If we do not resolve your request, you may complain to the Office of the Data Protection Commissioner (ODPC), Kenya.",
    ],
    body: "To exercise any right, email dpo@evidlens.co.ke from the email on your account. We will respond within 14 days, and may ask you to verify your identity first to prevent unauthorized disclosure.",
  },
  {
    id: "children",
    title: "11. Children",
    body: "EvidLens is for users aged 18 and over, and for businesses. We do not knowingly collect data from children under 18. If you believe a child has shared data with us, email dpo@evidlens.co.ke and we will delete it.",
  },
  {
    id: "changes",
    title: "12. Changes to This Policy",
    body: "If we change this policy materially, we will update the Last Updated date below and notify you by email or in-app notice at least 7 days before the change takes effect. Continued use after that date means you accept the updated policy.",
  },
  {
    id: "contact",
    title: "13. Contact Us",
    body: "Data Protection Officer: dpo@evidlens.co.ke. Support: support@evidlens.co.ke. EvidLens Ltd, Kenya. For account deletion, use Settings > Delete Account, or email the DPO from your account email.",
  },
];

export default function PrivacyPage() {
  return (
    <main className="bg-white text-gray-800">
      <div className="max-w-4xl mx-auto px-6 py-16">
        <p className="text-sm font-semibold text-teal-600 tracking-wide uppercase mb-2">
          EvidLens Ltd - Kenya
        </p>
        <h1 className="text-4xl font-bold mb-2">EvidLens Privacy Policy</h1>
        <p className="text-sm text-gray-500 mb-4">Last Updated: 25 November 2026</p>
        <p className="text-gray-600 mb-10">
          This policy applies to app.evidlens.co.ke, evidlens.co.ke, and all EvidLens
          products. It is written in plain language so you can understand what we do
          with your data. If anything is unclear, email{" "}
          <a href="mailto:dpo@evidlens.co.ke" className="text-teal-700 underline">
            dpo@evidlens.co.ke
          </a>
          .
        </p>

        <nav aria-label="Privacy policy sections" className="bg-gray-50 border rounded-xl p-4 mb-10">
          <p className="font-semibold text-sm mb-2">On this page</p>
          <ul className="grid sm:grid-cols-2 gap-1 text-sm">
            {SECTIONS.map((s) => (
              <li key={s.id}>
                <a href={`#${s.id}`} className="text-teal-700 hover:underline">
                  {s.title}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="space-y-10">
          {SECTIONS.map((section) => (
            <section key={section.id} id={section.id} className="scroll-mt-20">
              <h2 className="text-2xl font-semibold mb-3">{section.title}</h2>
              {section.body && <p className="leading-relaxed">{section.body}</p>}
              {section.list && (
                <ul className="list-disc pl-6 space-y-2 mt-3 leading-relaxed">
                  {section.list.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>

        <div className="mt-12 border-t pt-6 flex flex-wrap gap-4 text-sm">
          <Link href="/terms" className="text-teal-700 underline">
            Terms of Service
          </Link>
          <Link href="/contact" className="text-teal-700 underline">
            Contact Us
          </Link>
          <Link href="/" className="text-teal-700 underline">
            Back to Home
          </Link>
        </div>
      </div>
    </main>
  );
}
