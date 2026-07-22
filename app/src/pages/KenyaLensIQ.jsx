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
      <p className="text-gray-500 mb-6">Live Business Intelligence Terminal for Kenya</p>
      
      <button 
        onClick={handleTrial}
        disabled={startingTrial}
        className="mb-8 px-8 py-3 bg-green-600 text-white font-bold rounded-lg"
      >
        {startingTrial ? "Starting..." : "Start 7-Day Free Trial"}
      </button>
      
      <p className="text-sm text-gray-400 mb-8">Core + Health modules. Nairobi only. No card needed.</p>

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
export default function KenyaLensIQ() {
  const [loading, setLoading] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);
  const [sub, setSub] = useState(null);

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

  if(loading) return <div>Loading...</div>
  if(!hasAccess) return <PaymentPrompt />

  return (
    <>
      {sub.is_trial && <TrialBanner days={sub.days_left} />}
      <LensDashboardTabs allowedModules={sub.modules} />
    </>
  )
}

function TrialBanner({ days }) {
  const urgency = days <= 2 ? "bg-red-600" : "bg-orange-500"
  return (
    <div className={`${urgency} text-white p-3 text-center font-semibold`}>
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
