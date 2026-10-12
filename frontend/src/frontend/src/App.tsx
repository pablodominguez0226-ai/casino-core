import React, { useState, useEffect } from 'react'

export default function App() {
  const [backendStatus, setBackendStatus] = useState<string>('Comprobando...')

  useEffect(() => {
    fetch('/api/v1/health')
      .then((res) => res.json())
      .then((data) => setBackendStatus(data.status === 'ok' ? 'Conectado a FastAPI (200 OK)' : 'Error'))
      .catch(() => setBackendStatus('Sin conexión con el backend'))
  }, [])

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
      <h1 style={{ color: '#eab308', fontSize: '2.5rem', marginBottom: '0.5rem' }}>CasinoCore</h1>
      <p style={{ color: '#94a3b8', fontSize: '1.2rem', marginBottom: '2rem' }}>Gaming Management Platform — Interfaz React</p>
      
      <div style={{ background: '#1e293b', padding: '2rem', borderRadius: '12px', border: '1px solid #334155', minWidth: '320px', textAlign: 'center' }}>
        <h3 style={{ margin: '0 0 1rem 0' }}>Estado del Backend</h3>
        <span style={{ 
          display: 'inline-block',
          padding: '0.4rem 1rem', 
          borderRadius: '9999px', 
          fontSize: '0.9rem', 
          fontWeight: 'bold',
          background: backendStatus.includes('Conectado') ? '#14532d' : '#7f1d1d',
          color: backendStatus.includes('Conectado') ? '#4ade80' : '#f87171'
        }}>
          {backendStatus}
        </span>
      </div>
    </div>
  )
}
