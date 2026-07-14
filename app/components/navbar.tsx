'use client'
import Link from 'next/link'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Navbar() {
  const [user, setUser] = useState<any>(null)
  const [showDropdown, setShowDropdown] = useState(false)
  const [notifications, setNotifications] = useState(0)
  const router = useRouter()

  useEffect(() => {
    fetch('/auth/me', { credentials: 'include' })
      .then(res => res.json())
      .then(data => setUser(data))
      .catch(() => setUser(null))
    
    fetch('/api/notifications', { credentials: 'include' })
      .then(res => res.json())
      .then(data => setNotifications(data.count))
      .catch(() => setNotifications(0))
  }, [])

  const handleLogout = async () => {
    await fetch('/auth/logout', { method: 'POST', credentials: 'include' })
    router.push('/login')
  }

  if (!user) return null

  return (
    <nav className="bg-white border-b border-gray-200 px-4 md:px-6 py-3 flex justify-between items-center sticky top-0 z-50">
      <Link href="/dashboard" className="flex items-center gap-2">
        <div className="w-8 h-8 bg-[#2dd4bf] rounded flex items-center justify-center text-white font-bold">EL</div>
        <span className="font-bold text-xl text-[#1a2340]">EvidLens</span>
      </Link>

      <div className="flex items-center gap-3 md:gap-4">
        <div className="hidden md:flex items-center gap-2 bg-[#F0F9FF] px-3 py-1.5 rounded-lg border-[#bae6fd]">
          <span className="text-sm text-gray-600">Reports:</span>
          <span className="font-bold text-[#0ea5e9]">{user.reports_left}</span>
        </div>

        <button 
          onClick={() => router.push('/notifications')}
          className="relative p-2 hover:bg-gray-100 rounded-lg transition"
        >
          🔔
          {notifications > 0 && (
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          )}
        </button>

        <button 
          onClick={() => router.push('/pricing')}
          className="hidden md:block bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-orange-600 transition"
        >
          Upgrade
        </button>

        <div className="relative">
          <button 
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-2 p-1 hover:bg-gray-100 rounded-lg"
          >
            <img 
              src={user.avatar || `https://ui-avatars.com/api/?name=${user.email}`} 
              className="w-8 h-8 rounded-full bg-gray-300" 
              alt="avatar"
            />
            <span className="hidden md:block font-medium text-sm">{user.name || 'My Account'}</span>
            <span className="text-xs">▼</span>
          </button>
          
          {showDropdown && (
            <div className="absolute right-0 mt-2 w-56 bg-white shadow-xl rounded-lg py-2 border">
              <div className="px-4 py-2 border-b">
                <p className="font-semibold text-sm">{user.email}</p>
                <p className="text-xs text-gray-500">{user.plan} Plan</p>
              </div>
              
              <Link href="/dashboard" className="block px-4 py-2 hover:bg-gray-100 text-sm">Dashboard</Link>
              <Link href="/reports" className="block px-4 py-2 hover:bg-gray-100 text-sm">My Reports</Link>
              <Link href="/billing" className="block px-4 py-2 hover:bg-gray-100 text-sm">Billing & Subscription</Link>
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
    </nav>
  )
}
