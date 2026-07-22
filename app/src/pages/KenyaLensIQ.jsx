import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function KenyaLensIQ() {
  const [loading, setLoading] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);
  const [sub, setSub] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetch('/kenyalensiq/me', { headers: { Authorization: `Bearer ${localStorage.token}` }})
      .then(res => {
        if(res.status === 403) { setHasAccess(false) }
        else { 
          setHasAccess(true)
          return res.json()
        }
      })
      .then(data => setSub(data))
      .finally(() => setLoading(false))
  }, [])

  if(loading) return <div className="p-8">Loading...</div>
  if(!hasAccess) return <PaymentPrompt />

  return (
    <div className="p-6">
      {sub.is_trial && <TrialBanner days={sub.days_left} />}
      <LensDashboardTabs allowedModules={sub.modules} />
      {/* Here you render the actual charts for the selected tab */}
    </div>
  )
}

function TrialBanner({ days }) {
  const urgency = days <= 2 ? "bg-red-600" : "bg-orange-500"
  return (
    <div className={`${urgency} text-white p-3 mb-4 rounded-lg text-center font-semibold`}>
      ⚠️ {days} {days === 1 ? "day" : "days"} left in your free trial. 
      <button 
        onClick={() => window.location = `/billing/checkout?product=kenyalensiq&plan=Pro`}
        className="ml-3 underline font-bold"
      >
        Upgrade Now
      </button>
    </div>
  )
}

// PASTE THIS HERE 👇
function LensDashboardTabs({ allowedModules }) {
  const navigate = useNavigate();
  const allTabs = [
    {id: "core", name: "CORE"}, {id: "health", name: "HEALTH"}, 
    {id: "money", name: "MONEY"}, {id: "brand", name: "BRAND"},
    {id: "demand", name: "DEMAND"}, {id: "behavior", name: "BEHAVIOR"},
    {id: "policy", name: "POLICY"}, {id: "capital", name: "CAPITAL"},
    {id: "trade", name: "TRADE"}
  ]

  return (
    <div className="flex gap-2 border-b pb-3 mb-4 overflow-x-auto">
      {allTabs.map(tab => (
        <button 
          key={tab.id}
          disabled={!allowedModules.includes(tab.id)}
          className={`px-4 py-2 rounded-lg font-medium ${
            !allowedModules.includes(tab.id) 
              ? "opacity-40 cursor-not-allowed bg-gray-100" 
              : "bg-black text-white hover:bg-gray-800"
          }`}
          onClick={() => allowedModules.includes(tab.id) && navigate(`/kenyalensiq/${tab.id}`)}
        >
          {tab.name} {!allowedModules.includes(tab.id) && "🔒"}
        </button>
      ))}
    </div>
  )
}

function PaymentPrompt() {
  const [startingTrial, setStartingTrial] = useState(false)
  const plans = [
    {name: "Starter", price: "KES 800K/yr", modules: "2 modules, 1 region"},
    {name: "Pro", price: "KES 2M/yr", modules: "5 modules, 3 regions"},
    {name: "Enterprise", price: "KES 8M/yr", modules: "All 9 modules + API"}
  ]

  const handleTrial = async () => {
    setStartingTrial(true)
    const res = await fetch('/kenyalensiq/trial/start', {method: 'POST', headers: {Authorization: `Bearer ${localStorage.token}`}})
    if(res.ok) window.location.reload()
    else alert("Trial already used or error")
  }

  return (
    <div className="flex flex-col items-center justify-center h-screen">
      <div className="text-6xl mb-4">📊</div>
      <h1 className="text-3xl font-bold">Unlock KenyaLensIQ</h1>
      <button onClick={handleTrial} className="mt-4 px-8 py-3 bg-green-600 text-white rounded-lg">
        Start 7-Day Free Trial
      </button>
      {/* ...rest of plans */}
    </div>
  )
}
