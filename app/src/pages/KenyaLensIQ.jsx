import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function KenyaLensIQ() {
  const [loading, setLoading] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);
  const [plan, setPlan] = useState(null);

  useEffect(() => {
    fetch('/kenyalensiq/core', { headers: { Authorization: `Bearer ${localStorage.token}` }})
      .then(res => {
        if(res.status === 403) { setHasAccess(false) }
        else { setHasAccess(true) }
        setLoading(false)
      })
  }, [])

  if(loading) return <div>Loading...</div>

  if(!hasAccess) return <PaymentPrompt />

  return <LensDashboardTabs /> // your 9 tabs here
}

function PaymentPrompt() {
  const plans = [
    {name: "Starter", price: "KES 800K/yr", modules: "2 modules, 1 region"},
    {name: "Pro", price: "KES 2M/yr", modules: "5 modules, 3 regions"},
    {name: "Enterprise", price: "KES 8M/yr", modules: "All 9 modules + API"}
  ]

  return (
    <div className="flex flex-col items-center justify-center h-[80vh]">
      <div className="text-6xl mb-4">📊</div>
      <h1 className="text-3xl font-bold">Unlock KenyaLensIQ</h1>
      <p className="text-gray-500 mb-8">Live Business Intelligence Terminal for Kenya</p>
      
      <div className="grid grid-cols-3 gap-4">
        {plans.map(p => (
          <div key={p.name} className="border p-6 rounded-xl">
            <h3 className="font-bold text-xl">{p.name}</h3>
            <p className="text-2xl font-bold my-2">{p.price}</p>
            <p className="text-sm text-gray-500">{p.modules}</p>
            <button 
              onClick={() => window.location = `/billing/checkout?product=kenyalensiq&plan=${p.name}`}
              className="mt-4 w-full bg-black text-white py-2 rounded-lg"
            >
              Subscribe Now
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
