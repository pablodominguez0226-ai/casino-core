import React, { useState, useEffect } from 'react'

export default function App() {
  const [status, setStatus] = useState('Verificando conexión...')

  useEffect(() => {
    fetch('/api/v1/health')
      .then((res) => res.json())
      .then((data) => setStatus(data.status === 'ok' ? 'Conectado a FastAPI (200 OK)' : 'Error'))
      .catch(() => setStatus('Sin conexión con el backend'))
  }, [])

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
      <h1 style={{ color: '#eab308', fontSize: '2.5rem', margin: 0 }}>CasinoCore</h1>
      <p style={{ color: '#94a3b8', fontSize: '1.2rem', marginBottom: '2rem' }}>Gaming Management Platform — Frontend React</p>
      <div style={{ background: '#1e293b', padding: '1.5rem 2rem', borderRadius: '12px', border: '1px solid #334155', textAlign: 'center' }}>
        <p style={{ margin: '0 0 0.5rem 0', color: '#cbd5e1' }}>Estado del Backend:</p>
        <strong style={{ color: status.includes('Conectado') ? '#4ade80' : '#f87171' }}>{status}</strong>
      </div>
    </div>
  )
}
