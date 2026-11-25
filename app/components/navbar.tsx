"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type User = {
  name?: string;
  email?: string;
  avatar?: string;
  plan?: string;
  reports_left?: number;
  credits?: number;
};

const NAV_LINKS = [
  { label: "Demand", href: "/tools/demand" },
  { label: "Competitive", href: "/tools/competitive" },
  { label: "Risk", href: "/tools/risk" },
  { label: "Policy Watch", href: "/tools/policy" },
  { label: "Reports", href: "/tools/reports" },
  { label: "Pricing", href: "/pricing" },
];

export default function Navbar() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [showDropdown, setShowDropdown] = useState(false);
  const [showMobile, setShowMobile] = useState(false);
  const [notifications, setNotifications] = useState(0);
  const [planDisplay, setPlanDisplay] = useState("FREE");
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch("/api/me", { credentials: "include" });
        if (!res.ok) {
          if (!cancelled) setUser(null);
          return;
        }
        const data = await res.json().catch(() => null);
        if (!cancelled) setUser(data?.user || data || null);
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
      try {
        const res = await fetch("/api/notifications/count", { credentials: "include" });
        const data = await res.json().catch(() => null);
        if (!cancelled) setNotifications(Number(data?.count || data?.unread || 0) || 0);
      } catch {
        if (!cancelled) setNotifications(0);
      }
      try {
        const res = await fetch("/api/check-access", { credentials: "include" });
        const data = await res.json().catch(() => null);
        const raw = String(data?.plan || data?.plan_name || "FREE");
        const clean = raw.replace(/^EV-/, "").replace(/^EV_/, "").toUpperCase();
        if (!cancelled) setPlanDisplay(clean || "FREE");
      } catch {
        if (!cancelled) setPlanDisplay("FREE");
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setShowDropdown(false);
        setShowMobile(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const handleLogout = async () => {
    setShowDropdown(false);
    try {
      await fetch("/logout", { method: "POST", credentials: "include" });
    } catch {}
    try {
      localStorage.removeItem("token");
    } catch {}
    setUser(null);
    router.push("/login?logged_out=1");
    router.refresh();
  };

  const avatarUrl = user?.avatar
    ? user.avatar
    : `https://ui-avatars.com/api/?name=${encodeURIComponent(user?.name || user?.email || "E")}&background=14B8A6&color=fff`;

  return (
    <nav className="bg-white border-b border-gray-200 px-4 md:px-6 py-3 flex justify-between items-center sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowMobile(!showMobile)}
          className="md:hidden p-2 hover:bg-gray-100 rounded-lg"
          aria-label="Toggle menu"
        >
          ☰
        </button>
        <Link href={user ? "/dashboard" : "/"} className="flex items-center gap-2">
          <div className="w-8 h-8 bg-[#2dd4bf] rounded flex items-center justify-center text-white font-bold">EL</div>
          <span className="font-bold text-xl text-[#1a2340]">EvidLens</span>
        </Link>
        <div className="hidden lg:flex items-center gap-4 ml-6">
          {NAV_LINKS.map((l) => (
            <Link key={l.href} href={l.href} className="text-sm text-gray-600 hover:text-gray-900">
              {l.label}
            </Link>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="w-32 h-9 bg-gray-100 rounded-lg animate-pulse" />
      ) : !user ? (
        <div className="flex items-center gap-2">
          <Link href="/login" className="px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-100">
            Login
          </Link>
          <Link href="/signup" className="bg-[#0A1F44] text-white px-4 py-2 rounded-lg text-sm font-semibold">
            Start Free
          </Link>
        </div>
      ) : (
        <div className="flex items-center gap-3 md:gap-4">
          <div className="hidden md:flex items-center gap-2 bg-[#F0F9FF] px-3 py-1.5 rounded-lg border border-[#bae6fd]">
            <span className="text-sm text-gray-600">Credits:</span>
            <span className="font-bold text-[#0ea5e9]">{user.credits ?? "—"}</span>
          </div>
          <div className="hidden md:flex items-center gap-2 bg-gray-50 px-3 py-1.5 rounded-lg border">
            <span className="text-sm text-gray-600">Plan:</span>
            <span className="font-bold text-sm">{planDisplay}</span>
          </div>

          <button
            onClick={() => router.push("/notifications")}
            className="relative p-2 hover:bg-gray-100 rounded-lg transition"
            aria-label="Notifications"
          >
            🔔
            {notifications > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
            )}
          </button>

          {planDisplay !== "ENTERPRISE" && (
            <button
              onClick={() => router.push("/pricing")}
              className="hidden md:block bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-orange-600 transition"
            >
              Upgrade
            </button>
          )}

          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className="flex items-center gap-2 p-1 hover:bg-gray-100 rounded-lg"
              aria-haspopup="menu"
              aria-expanded={showDropdown}
            >
              <img
                src={avatarUrl}
                className="w-8 h-8 rounded-full bg-gray-300 object-cover"
                alt="avatar"
              />
              <span className="hidden md:block font-medium text-sm max-w-[120px] truncate">{user.name || "My Account"}</span>
              <span className="text-xs">▼</span>
            </button>

            {showDropdown && (
              <div className="absolute right-0 mt-2 w-56 bg-white shadow-xl rounded-lg py-2 border z-50">
                <div className="px-4 py-2 border-b">
                  <p className="font-semibold text-sm truncate">{user.email}</p>
                  <p className="text-xs text-gray-500">{planDisplay} Plan • {user.credits ?? 0} credits</p>
                </div>
                <Link href="/dashboard" className="block px-4 py-2 hover:bg-gray-100 text-sm">Dashboard</Link>
                <Link href="/reports" className="block px-4 py-2 hover:bg-gray-100 text-sm">My Reports</Link>
                <Link href="/billing" className="block px-4 py-2 hover:bg-gray-100 text-sm">Billing & Subscription</Link>
                <Link href="/wallet" className="block px-4 py-2 hover:bg-gray-100 text-sm">Wallet & Credits</Link>
                <Link href="/settings" className="block px-4 py-2 hover:bg-gray-100 text-sm">Settings</Link>
                <hr className="my-2" />
                <button
                  onClick={handleLogout}
                  className="block w-full text-left px-4 py-2 hover:bg-gray-100 text-sm text-red-600"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {showMobile && (
        <div className="absolute top-full left-0 right-0 bg-white border-b shadow-lg md:hidden px-4 py-3 flex flex-col gap-2">
          {NAV_LINKS.map((l) => (
            <Link key={l.href} href={l.href} onClick={() => setShowMobile(false)} className="py-2 text-sm">
              {l.label}
            </Link>
          ))}
          {!user && (
            <>
              <Link href="/login" onClick={() => setShowMobile(false)} className="py-2 text-sm font-semibold">Login</Link>
              <Link href="/signup" onClick={() => setShowMobile(false)} className="py-2 text-sm font-semibold">Start Free</Link>
            </>
          )}
        </div>
      )}
    </nav>
  );
}
