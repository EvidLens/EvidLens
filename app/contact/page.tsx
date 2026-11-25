"use client";

import { useState } from "react";

const CHANNELS = [
  {
    title: "WhatsApp",
    value: "+254 725 095 956",
    href: "https://wa.me/254725095956?text=Hi%20EvidLens%2C%20I%20need%20help%20with%20",
    action: "Chat on WhatsApp",
  },
  {
    title: "Email - Support",
    value: "support@evidlens.co.ke",
    href: "mailto:support@evidlens.co.ke",
    action: "Email Support",
  },
  {
    title: "Email - Privacy / DPO",
    value: "dpo@evidlens.co.ke",
    href: "mailto:dpo@evidlens.co.ke",
    action: "Email DPO",
  },
  {
    title: "Hours",
    value: "Mon - Fri: 8:00 AM - 6:00 PM EAT",
    href: "",
    action: "",
  },
  {
    title: "Office",
    value: "Nyeri, Kenya",
    href: "",
    action: "",
  },
];

export default function ContactPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [topic, setTopic] = useState("Support");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("");
  const [sending, setSending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !message.trim()) {
      setStatus("Please fill name, email, and message.");
      return;
    }
    setSending(true);
    setStatus("");
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, topic, message }),
      });
      if (res.ok) {
        setStatus("Sent! We will reply within 2 hours during business hours.");
        setName("");
        setEmail("");
        setMessage("");
        return;
      }
      throw new Error("Failed");
    } catch {
      window.location.href = `mailto:support@evidlens.co.ke?subject=${encodeURIComponent(
        `[${topic}] Contact from ${name}`
      )}&body=${encodeURIComponent(`${message}\n\nFrom: ${name} (${email})`)}`;
      setStatus("Could not send via form - your email app opened instead.");
    } finally {
      setSending(false);
    }
  }

  return (
    <main className="bg-white text-gray-800">
      <div className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-4xl font-bold mb-2">Contact EvidLens Support</h1>
        <p className="text-gray-500 mb-6">
          Payment issue, report not generating, or question about your plan? We reply fast.
        </p>
        <div className="bg-[#F0F9FF] p-6 rounded-lg mb-10">
          <p className="font-semibold text-[#0ea5e9]">
            Response Time: &lt; 2 Hours during business hours (Mon - Fri, 8am - 6pm EAT)
          </p>
          <p className="text-sm text-gray-600 mt-1">
            For M-Pesa issues, include your M-Pesa Receipt Number and phone number - we can trace it in minutes.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-10">
          <div>
            <h2 className="text-xl font-bold mb-4">Reach us directly</h2>
            <div className="space-y-5">
              {CHANNELS.map((c) => (
                <div key={c.title}>
                  <h3 className="font-bold">{c.title}</h3>
                  <p className="text-gray-600">{c.value}</p>
                  {c.href && (
                    <a href={c.href} className="text-sm text-teal-700 underline">
                      {c.action}
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h2 className="text-xl font-bold mb-4">Send us a message</h2>
            <form onSubmit={onSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold mb-1">Name</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2"
                  placeholder="Your full name"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-semibold mb-1">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2"
                  placeholder="you@example.com"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-semibold mb-1">Topic</label>
                <select
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2"
                >
                  <option>Support</option>
                  <option>Payment / M-Pesa</option>
                  <option>Billing / Subscription</option>
                  <option>Privacy / DPO</option>
                  <option>Partnership</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold mb-1">Message</label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2"
                  rows={5}
                  placeholder="Describe your issue - include M-Pesa receipt if payment related"
                  required
                />
              </div>
              {status && (
                <p className="text-sm bg-gray-50 border rounded-lg p-3">{status}</p>
              )}
              <button
                type="submit"
                disabled={sending}
                className="w-full bg-[#0A1F44] text-white py-3 rounded-lg font-bold disabled:opacity-50"
              >
                {sending ? "Sending..." : "Send Message"}
              </button>
              <p className="text-xs text-gray-500 text-center">
                Never share your M-Pesa PIN or password. EvidLens will never ask for them.
              </p>
            </form>
          </div>
        </div>
      </div>
    </main>
  );
}
