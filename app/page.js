'use client'
export default function Home() {
  return (
    <div style={{padding: '40px', textAlign: 'center', fontFamily: 'system-ui'}}>
      <h1 style={{color: '#0A1F44'}}>EvidLens</h1>
      <p>Kenya's Decision Intelligence Platform</p>
      
      <button onClick={() => window.location.href = '/chat'} style={{background: '#14B8A6', color: 'white', padding: '14px', border: 'none', borderRadius: '8px', width: '200px', margin: '10px', cursor: 'pointer'}}>Ask Lens AI</button>
      <br/>
      <button onClick={() => window.location.href = '/lanes'} style={{background: 'white', color: '#0A1F44', padding: '14px', border: '2px solid #14B8A6', borderRadius: '8px', width: '200px', margin: '10px', cursor: 'pointer'}}>Browse 9 Lanes</button>
      <br/>
      <button onClick={() => window.location.href = '/login'} style={{background: 'white', color: '#0A1F44', padding: '14px', border: '2px solid #e2e8f0', borderRadius: '8px', width: '200px', margin: '10px', cursor: 'pointer'}}>Login</button>
    </div>
  )
}
