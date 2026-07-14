export default function Footer() {
  return (
    <footer className="bg-[#0F1A2E] text-white pt-12 pb-6">
      <div className="max-w-7xl mx-auto px-6 grid-cols-2 md:grid-cols-4 gap-8">
        
        {/* Legal */}
        <div>
          <h3 className="text-teal-400 font-semibold mb-4">Legal</h3>
          <ul className="space-y-2 text-sm text-gray-300">
            <li><a href="/privacy" className="hover:text-white">Privacy Policy</a></li>
            <li><a href="/terms" className="hover:text-white">Terms</a></li>
          </ul>
        </div>

        {/* Support */}
        <div>
          <h3 className="text-teal-400 font-semibold mb-4">Support</h3>
          <ul className="space-y-2 text-sm text-gray-300">
            <li><a href="/contact" className="hover:text-white">Contact Us</a></li>
          </ul>
        </div>

        {/* Product */}
        <div>
          <h3 className="text-teal-400 font-semibold mb-4">Product</h3>
          <ul className="space-y-2 text-sm text-gray-300">
            <li><a href="/pricing" className="hover:text-white">Pricing</a></li>
          </ul>
        </div>

        {/* Company */}
        <div>
          <h3 className="text-teal-400 font-semibold mb-4">Company</h3>
          <ul className="space-y-2 text-sm text-gray-300">
            <li><a href="/about" className="hover:text-white">About</a></li>
          </ul>
        </div>
      </div>

      <div className="border-t border-gray-700 mt-8 pt-6 text-center text-xs text-gray-400">
        © 2026 EvidLens. Decision Intelligence for Kenyan SMEs.
      </div>
    </footer>
  )
}
