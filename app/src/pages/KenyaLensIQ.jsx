import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

export default function KenyaLensIQ() {
  const [loading, setLoading] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);
  const [sub, setSub] = useState(null);
  const [activeTab, setActiveTab] = useState("core");
  const [data, setData] = useState(null);
  const navigate = useNavigate();
  const { tab } = useParams(); // /kenyalensiq/:tab

  useEffect(() => {
    if(tab) setActiveTab(tab)
  }, [tab])

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

  // Load data when tab changes
  useEffect(() => {
    if(!hasAccess ||!sub) return;
    if(!sub.modules.includes(activeTab)) return; // block locked tabs

    setLoading(true)
    fetch(`/kenyalensiq/${activeTab}`, { headers: { Authorization: `Bearer ${localStorage.token}` }})
     .then(res => res.json())
     .then(d => setData(d))
     .finally(() => setLoading(false))
  }, [activeTab, hasAccess, sub])

  if(loading &&!data) return <div className="p-8">Loading...</div>
  if(!hasAccess) return <PaymentPrompt />

  return (
    <div className="p-6">
      {sub.is_trial && <TrialBanner days={sub.days_left} />}
      <LensDashboardTabs
        allowedModules={sub.modules}
        activeTab={activeTab}
        onTabClick={(id) => {
          if(sub.modules.includes(id)) navigate(`/kenyalensiq/${id}`)
        }}
      />

      <TabContent tab={activeTab} data={data} loading={loading} />
    </div>
  )
}

function TabContent({ tab, data, loading }) {
  if(loading) return <div>Loading {tab} data...</div>
  if(!data) return <div>Select a tab</div>

  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="border p-4 rounded-xl">
        <h3 className="font-bold">Total {tab}</h3>
        <p className="text-3xl">{data.count || 0}</p>
      </div>
      <div className="border p-4 rounded-xl col-span-2">
        <h3 className="font-bold">Trend</h3>
        {/* Paste your chart here. data.chartData */}
        <pre className="text-xs">{JSON.stringify(data, null, 2)}</pre>
      </div>
    </div>
  )
}

function LensDashboardTabs({ allowedModules, activeTab, onTabClick }) {
  const allTabs = [
    {id: "core", name: "CORE"}, {id: "health", name: "HEALTH"},
    {id: "money", name: "MONEY"}, {id: "brand", name: "BRAND"},
    {id: "demand", name: "DEMAND"}, {id: "behavior", name: "BEHAVIOR"},
    {id: "policy", name: "POLICY"}, {id: "capital", name: "CAPITAL"},
    {id: "trade", name: "TRADE"}
  ]

  return (
    <div className="flex gap-2 border-b pb-3 mb-4 overflow-x-auto">
      {allTabs.map(tab => {
        const isAllowed = allowedModules.includes(tab.id)
        const isActive = activeTab === tab.id
        return (
          <button
            key={tab.id}
            disabled={!isAllowed}
            onClick={() => onTabClick(tab.id)}
            className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap ${
             !isAllowed
               ? "opacity-40 cursor-not-allowed bg-gray-100"
                : isActive
                 ? "bg-black text-white"
                  : "bg-gray-200 hover:bg-gray-300"
            }`}
          >
            {tab.name} {!isAllowed && "🔒"}
          </button>
        )
      })}
    </div>
  )
}

function TrialBanner({ days }) { /* same as before */ }
function PaymentPrompt() { /* same as before */ }
