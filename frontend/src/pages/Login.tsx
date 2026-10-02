import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { auth } from '../api/client'
import { Landmark, ShieldCheck, Lock, AlertCircle } from 'lucide-react'

export default function Login() {
  const [email, setEmail] = useState('demo@dualtrust.ai')
  const [password, setPassword] = useState('demo1234')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const r = await auth.login(email, password)
      localStorage.setItem('token', r.data.access_token)
      navigate('/')
    } catch {
      setError('Invalid officer credentials. Please check your banking employee ID.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: '#f1f5f9',
    }}>
      {/* Top Bank Institutional Bar */}
      <div style={{
        background: '#0a1829',
        color: '#94a3b8',
        padding: '10px 32px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '11px',
        letterSpacing: '0.05em',
        borderBottom: '1px solid #1a2a40'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#f8fafc', fontWeight: 600 }}>
          <Landmark size={15} color="#38bdf8" />
          <span>DUALTRUST FINANCIAL CORP — COMMERCIAL UNDERWRITING PORTAL</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ color: '#4ade80' }}>● SECURE GATEWAY (TLS 1.3)</span>
        </div>
      </div>

      {/* Main Login Card Area */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}>
        <div style={{ width: '100%', maxWidth: 420 }}>
          {/* Bank Badge */}
          <div style={{ textAlign: 'center', marginBottom: 28 }}>
            <div style={{
              width: 52,
              height: 52,
              background: '#0f243d',
              borderRadius: 8,
              margin: '0 auto 14px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              border: '1px solid #1e3a8a',
              boxShadow: '0 4px 12px rgba(15, 23, 42, 0.15)'
            }}>
              <Landmark size={26} />
            </div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--bank-navy)', letterSpacing: '-0.3px' }}>
              DualTrust Bancorp
            </h1>
            <p style={{ color: 'var(--bank-text-muted)', fontSize: 13, marginTop: 4 }}>
              Credit Risk &amp; Document Underwriting Station
            </p>
          </div>

          {/* Form Card */}
          <div className="card" style={{ borderTop: '4px solid var(--bank-navy)', padding: '28px 24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 18 }}>
              <Lock size={15} color="var(--bank-navy)" />
              <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--bank-navy)' }}>
                Officer Authentication
              </span>
            </div>

            <form onSubmit={handleLogin} style={{ display: 'grid', gap: 16 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--bank-text-secondary)', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Officer Email / ID
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', fontSize: 14 }}
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--bank-text-secondary)', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Security Passphrase
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', fontSize: 14 }}
                  required
                />
              </div>

              {error && (
                <div style={{
                  background: 'var(--risk-fail-bg)',
                  border: '1px solid var(--risk-fail-border)',
                  color: 'var(--risk-fail-text)',
                  padding: '9px 12px',
                  borderRadius: 5,
                  fontSize: 12.5,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8
                }}>
                  <AlertCircle size={15} />
                  <span>{error}</span>
                </div>
              )}

              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
                style={{ padding: '11px', width: '100%', marginTop: 4, fontSize: 13.5 }}
              >
                {loading ? 'Authenticating with Ledger...' : 'Access Underwriting Terminal →'}
              </button>
            </form>

            <div style={{
              marginTop: 20,
              padding: '10px 12px',
              background: 'var(--bank-canvas)',
              borderRadius: 5,
              border: '1px solid var(--bank-border)',
              fontSize: 11.5,
              color: 'var(--bank-text-muted)'
            }}>
              <strong>Underwriter Simulation</strong>: Credentials pre-loaded for review demonstration (<code style={{ color: 'var(--bank-navy)' }}>demo@dualtrust.ai</code>).
            </div>
          </div>

          {/* Statutory Security Disclaimer */}
          <div style={{ textAlign: 'center', marginTop: 18, fontSize: 11, color: 'var(--bank-text-muted)', lineHeight: 1.5 }}>
            Internal banking system. Authorized access only. All sessions, document extractions, and underwriting reviews are logged under Banking Regulation Act standards.
          </div>
        </div>
      </div>
    </div>
  )
}
