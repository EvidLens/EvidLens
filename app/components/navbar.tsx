'use client'
import Link from 'next/link'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Navbar() {
  const [user, setUser] = useState<any>(null) // Stores user data from backend
  const [showDropdown, setShowDropdown] = useState(false) // Controls "My Account" dropdown
  const [notifications, setNotifications] = useState(1) // Demo: unread notification count
  const router = useRouter()

  // 1. FETCH USER DATA ON LOAD
  // This calls backend /api/v1/auth/me to get: email, plan, reports_left
  // This is what powers the "Credits Balance" and "My Account" dropdown
  useEffect(() => {
    fetch('/api/v1/auth/me', { credentials: 'include' }) // include cookies for auth
      .then(res => res.json())
      .then(data => setUser(data))
      .catch(() => setUser(null)) // if not logged in, hide navbar
  }, [])

  // LOGOUT FUNCTION
  // Calls backend to clear session cookie, then redirects to login
  const handleLogout = async () => {
    await fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' })
    router.push('/login')
  }

  if (!user) return null // Don't show navbar if user not logged in

  return (
    <nav className="bg-white border-b border-gray-200 px-4 md:px-6 py-3 flex justify-between items-center sticky top-0 z-50">
      {/* LEFT: LOGO - Click goes to dashboard */}
      <Link href="/dashboard" className="flex items-center gap-2">
        <div className="w-8 h-8 bg-[#2dd4bf] rounded flex items-center justify-center text-white font-bold">EL</div>
        <span className="font-bold text-xl text-[#1a2340]">EvidLens</span>
      </Link>

      {/* RIGHT: 4 INTERCONNECTED ITEMS */}
      <div className="flex items-center gap-3 md:gap-4">
        
        {/* ITEM 1: CREDITS BALANCE 
           Reads from user.reports_left from /auth/me
           Updates automatically when user buys report or generates one
           Hidden on mobile to save space
        */}
        <div className="hidden md:flex items-center gap-2 bg-[#F0F9FF] px-3 py-1.5 rounded-lg border-[#bae6fd]">
          <span className="text-sm text-gray-600">Reports:</span>
          <span className="font-bold text-[#0ea5e9]">{user.reports_left}</span>
        </div>

        {/* ITEM 2: NOTIFICATIONS BELL
           Click goes to /notifications page
           Red dot shows if notifications > 0
           Backend should return count from /api/v1/notifications
        */}
        <button 
          onClick={() => router.push('/notifications')}
          className="relative p-2 hover:bg-gray-100 rounded-lg transition"
        >
          🔔
          {notifications > 0 && (
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span> // Red dot badge
          )}
        </button>

        {/* ITEM 3: UPGRADE BUTTON
           Only shows on desktop
           Click goes to /pricing page
           Connected to /payments/buy-report backend
        */}
        <button 
          onClick={() => router.push('/pricing')}
          className="hidden md:block bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-orange-600 transition"
        >
          Upgrade
        </button>

        {/* ITEM 4: MY ACCOUNT DROPDOWN
           Click avatar to toggle dropdown
           Shows: email, plan, and links to Dashboard, Reports, Billing, Settings, Logout
           All links are interconnected with backend pages
        */}
        <div className="relative">
          <button 
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-2 p-1 hover:bg-gray-100 rounded-lg"
          >
            {/* Avatar: Uses user avatar or generates one from email */}
            <img 
              src={user.avatar || `https://ui-avatars.com/api/?name=${user.email}`} 
              className="w-8 h-8 rounded-full bg-gray-300" 
              alt="avatar"
            />
            <span className="hidden md:block font-medium text-sm">{user.name || 'My Account'}</span>
            <span className="text-xs">▼</span>
          </button>
          
          {/* DROPDOWN MENU - Only shows when showDropdown = true */}
          {showDropdown && (
            <div className="absolute right-0 mt-2 w-56 bg-white shadow-xl rounded-lg py-2 border">
              {/* User Info Header */}
              <div className="px-4 py-2 border-b">
                <p className="font-semibold text-sm">{user.email}</p>
                <p className="text-xs text-gray-500">{user.plan} Plan</p>
              </div>
              
              {/* Navigation Links - All must have pages */}
              <Link href="/dashboard" className="block px-4 py-2 hover:bg-gray-100 text-sm">Dashboard</Link>
              <Link href="/reports" className="block px-4 py-2 hover:bg-gray-100 text-sm">My Reports</Link>
              <Link href="/billing" className="block px-4 py-2 hover:bg-gray-100 text-sm">Billing & Subscription</Link>
              <Link href="/settings" className="block px-4 py-2 hover:bg-gray-100 text-sm">Settings</Link>
              
              <hr className="my-2" />
              {/* Logout Button - Calls handleLogout function */}
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
    </nav>
  )
}
