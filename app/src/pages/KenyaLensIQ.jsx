import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, AreaChart, Area, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

const COLORS = ['#000000', '#4B5563', '#9CA3AF', '#D1D5DB', '#F3F4F6'];

export default function KenyaLensIQ() {
  const [loading, setLoading] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);
  const [sub, setSub] = useState(null);
  const [activeTab, setActiveTab] = useState("core");
  const [data, setData] = useState(null);
  const navigate = useNavigate();
  const { tab } = useParams();

  useEffect(() => { if(tab) setActiveTab(tab) }, [tab])

  useEffect(() => {
    fetch('/kenyalensiq/me', { headers: { Authorization: `Bearer ${localStorage.token}` }})
    .then(res => res.status === 403? setHasAccess(false) : res.json().then(d => {setHasAccess(true); setSub(d)}))
    .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if(!hasAccess ||!sub) return;
    if(!sub.modules.includes(activeTab)) return;
    setLoading(true)
    fetch(`/kenyalensiq/${activeTab}`, { headers: { Authorization: `Bearer ${localStorage.token}` }})
    .then(res => res.json()).then(d => setData(d)).finally(() => setLoading(false))
  }, [activeTab, hasAccess, sub])

  const handleExport = () => {
    window.location = `/kenyalensiq/export?module=${activeTab}&token=${localStorage.token}`
  }

  if(loading &&!data) return <div className="p-8">Loading...</div>
  if(!hasAccess) return <PaymentPrompt />

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {sub.is_trial && <TrialBanner days={sub.days_left} />}
      <div className="flex justify-between items-center mb-4">
        <LensDashboardTabs allowedModules={sub.modules} activeTab={activeTab} onTabClick={(id) => sub.modules.includes(id) && navigate(`/kenyalensiq/${id}`)} />
        <button onClick={handleExport} className="px-4 py-2 border rounded-lg">Export CSV</button>
      </div>
      <TabRouter tab={activeTab} data={data} loading={loading} isAllowed={sub.modules.includes(activeTab)} />
    </div>
  )
}

function TabRouter({ tab, data, loading, isAllowed }) {
  if(!isAllowed) return <LockedTab tab={tab} />
  if(loading) return <div>Loading {tab}...</div>

  const map = {
    core: <CoreTab data={data} />,
    health: <HealthTab data={data} />,
    money: <MoneyTab data={data} />,
    brand: <BrandTab data={data} />,
    demand: <DemandTab data={data} />,
    behavior: <BehaviorTab data={data} />,
    policy: <PolicyTab data={data} />,
    capital: <CapitalTab data={data} />,
    trade: <TradeTab data={data} />,
  }
  return map[tab] || <div>No data</div>
}

function KpiCard({ title, value, sub }) {
  return (
    <div className="border p-4 rounded-xl">
      <p className="text-sm text-gray-500">{title}</p>
      <p className="text-3xl font-bold">{value}</p>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </div>
  )
}

function LockedTab({ tab }) {
  return (
    <div className="border-2 border-dashed rounded-xl p-12 text-center">
      <div className="text-5xl mb-4">🔒</div>
      <h3 className="text-2xl font-bold">{tab.toUpperCase()} is locked</h3>
      <p className="text-gray-500 mb-4">Upgrade to unlock this module</p>
      <button onClick={() => window.location = `/billing/checkout?product=kenyalensiq&plan=Pro`} className="bg-black text-white px-6 py-2 rounded-lg">Upgrade</button>
    </div>
  )
}

// ====== 9 TAB COMPONENTS ======
function CoreTab({ data }) {
  return (
    <>
      <div className="grid grid-cols-4 gap-4 mb-4">
        <KpiCard title="Total Businesses" value={data.count} />
        <KpiCard title="New This Month" value={data.new_count} sub="+12%" />
        <KpiCard title="Top Sector" value={data.top_sector} />
        <KpiCard title="Counties Covered" value={data.counties} />
      </div>
      <div className="border p-4 rounded-xl">
        <h3 className="font-bold mb-2">Businesses by Sector</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data.by_sector}><XAxis dataKey="name" /><YAxis /><Tooltip /><Bar dataKey="count" fill="#000" /></BarChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}

function HealthTab({ data }) {
  return (
    <>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <KpiCard title="Health Score" value={`${data.health_score}%`} />
        <KpiCard title="New Registrations" value={data.new} />
        <KpiCard title="Closures" value={data.closed} />
      </div>
      <div className="border p-4 rounded-xl">
        <h3 className="font-bold mb-2">Health Trend 6M</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data.trend}><XAxis dataKey="month" /><YAxis /><Tooltip /><Line type="monotone" dataKey="score" stroke="#000" /></LineChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}

function MoneyTab({ data }) {
  return (
    <>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <KpiCard title="Est. Revenue" value={`KES ${data.revenue}`} />
        <KpiCard title="Funding Rounds" value={data.rounds} />
        <KpiCard title="Avg Ticket" value={`KES ${data.avg_ticket}`} />
      </div>
      <div className="border p-4 rounded-xl">
        <h3 className="font-bold mb-2">Funding Over Time</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data.funding}><XAxis dataKey="month" /><YAxis /><Tooltip /><Area type="monotone" dataKey="amount" stroke="#000" fill="#000" /></AreaChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}

function BrandTab({ data }) {
  return (
    <>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <KpiCard title="Mentions" value={data.mentions} />
        <KpiCard title="Sentiment" value={`${data.sentiment}%`} />
        <KpiCard title="Top Brand" value={data.top_brand} />
      </div>
      <div className="border p-4 rounded-xl">
        <h3 className="font-bold mb-2">Sentiment Breakdown</h3>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart><Pie data={data.sentiment_breakdown} dataKey="value" nameKey="name"><{data.sentiment_breakdown?.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /></PieChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}

function DemandTab({ data }) {
  return (
    <>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <KpiCard title="Search Volume" value={data.searches} />
        <KpiCard title="Top Keyword" value={data.top_keyword} />
        <KpiCard title="YoY Growth" value={`${data.growth}%`} />
      </div>
      <div className="border p-4 rounded-xl">
        <h3 className="font-bold mb-2">Trending Products</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data.trending}><XAxis dataKey="name" /><YAxis /><Tooltip /><Bar dataKey="volume" fill="#000" /></BarChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}

function BehaviorTab({ data }) {
  return (
    <>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <KpiCard title="Avg Basket" value={`KES ${data.avg_basket}`} />
        <KpiCard title="Repeat Rate" value={`${data.repeat}%`} />
        <KpiCard title="Top Category" value={data.top_category} />
      </div>
      <div className="border p-4 rounded-xl">
        <h3 className="font-bold mb-2">Customer Journey Funnel</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data.funnel} layout="vertical"><XAxis type="number" /><YAxis dataKey="stage" type="category" /><Tooltip /><Bar dataKey="users" fill="#000" /></BarChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}

function PolicyTab({ data }) {
  return (
    <>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <KpiCard title="New Policies" value={data.new_policies} />
        <KpiCard title="High Risk Counties" value={data.risk_counties} />
        <KpiCard title="Compliance Score" value={`${data.compliance}%`} />
      </div>
      <div className="border p-4 rounded-xl">
        <h3 className="font-bold mb-2">Policy Timeline</h3>
        <ul>{data.timeline?.map(p => <li key={p.id} className="border-b py-2">{p.date} - {p.title}</li>)}</ul>
      </div>
    </>
  )
}

function CapitalTab({ data }) {
  return (
    <>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <KpiCard title="Active Investors" value={data.investors} />
        <KpiCard title="Deals YTD" value={data.deals} />
        <KpiCard title="Capital Raised" value={`KES ${data.raised}`} />
      </div>
      <div className="border p-4 rounded-xl">
        <h3 className="font-bold mb-2">Top Deals</h3>
        <table className="w-full text-sm"><tbody>{data.deals_list?.map(d => <tr key={d.id}><td>{d.company}</td><td>{d.investor}</td><td>KES {d.amount}</td></tr>)}</tbody></table>
      </div>
    </>
  )
}

function TradeTab({ data }) {
  return (
    <>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <KpiCard title="Exports" value={`KES ${data.exports}`} />
        <KpiCard title="Imports" value={`KES ${data.imports}`} />
        <KpiCard title="Trade Balance" value={`KES ${data.balance}`} />
      </div>
      <div className="border p-4 rounded-xl">
        <h3 className="font-bold mb-2">Top Destinations</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data.destinations}><XAxis dataKey="country" /><YAxis /><Tooltip /><Bar dataKey="value" fill="#000" /></BarChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}

function TrialBanner({ days }) {
  const urgency = days <= 2? "bg-red-600" : "bg-orange-500"
  return (
    <div className={`${urgency} text-white p-3 mb-4 rounded-lg text-center font-semibold`}>
      ⚠️ {days} {days === 1? "day" : "days"} left in your free trial.
      <button onClick={() => window.location = `/billing/checkout?product=kenyalensiq&plan=Pro`} className="ml-3 underline font-bold">Upgrade Now</button>
    </div>
  )
}

function LensDashboardTabs({ allowedModules, activeTab, onTabClick }) {
  const allTabs = [
    {id: "core", name: "CORE"}, {id: "health", name: "HEALTH"}, {id: "money", name: "MONEY"}, {id: "brand", name: "BRAND"},
    {id: "demand", name: "DEMAND"}, {id: "behavior", name: "BEHAVIOR"}, {id: "policy", name: "POLICY"}, {id: "capital", name: "CAPITAL"}, {id: "trade", name: "TRADE"}
  ]
  return (
    <div className="flex gap-2 border-b pb-3 overflow-x-auto">
      {allTabs.map(tab => {
        const isAllowed = allowedModules.includes(tab.id)
        const isActive = activeTab === tab.id
        return (
          <button key={tab.id} disabled={!isAllowed} onClick={() => onTabClick(tab.id)}
            className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap ${!isAllowed? "opacity-40 cursor-not-allowed bg-gray-100" : isActive? "bg-black text-white" : "bg-gray-200 hover:bg-gray-300"}`}>
            {tab.name} {!isAllowed && "🔒"}
          </button>
        )
      })}
    </div>
  )
}

function PaymentPrompt() {
  const [startingTrial, setStartingTrial] = useState(false)
  const handleTrial = async () => {
    setStartingTrial(true)
    const res = await fetch('/kenyalensiq/trial/start', {method: 'POST', headers: {Authorization: `Bearer ${localStorage.token}`}})
    if(res.ok) window.location.reload()
    else alert("Trial already used")
  }
  return (
    <div className="flex flex-col items-center justify-center h-screen">
      <div className="text-6xl mb-4">📊</div><h1 className="text-3xl font-bold">Unlock KenyaLensIQ</h1>
      <button onClick={handleTrial} disabled={startingTrial} className="mt-4 px-8 py-3 bg-green-600 text-white rounded-lg">Start 7-Day Free Trial</button>
    </div>
  )
}
