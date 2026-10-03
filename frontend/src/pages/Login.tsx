import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { auth } from '../api/client'
import { ShieldCheck, Lock, AlertCircle } from 'lucide-react'
import { LogoIcon, DualTrustLogo } from '../components/Logo'

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
          <div style={{
            background: '#ffffff',
            borderRadius: 4,
            padding: '2px 4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <LogoIcon size={13} />
          </div>
          <span>DUALTRUST <span style={{ color: '#f79f1a' }}>AI</span> — COMMERCIAL UNDERWRITING PORTAL</span>
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
        <div style={{ width: '100%', maxWidth: 440 }}>
          {/* DualTrust AI Official Logo Banner */}
          <div style={{ textAlign: 'center', marginBottom: 26 }}>
            <div style={{
              display: 'inline-flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '24px 36px 20px',
              background: '#ffffff',
              borderRadius: 16,
              boxShadow: '0 10px 25px -5px rgba(15, 23, 42, 0.08), 0 8px 10px -6px rgba(15, 23, 42, 0.04)',
              border: '1px solid #e2e8f0',
              marginBottom: 12,
            }}>
              <DualTrustLogo variant="full" size="md" />
            </div>
            <p style={{ color: 'var(--bank-text-muted)', fontSize: 13, marginTop: 4, fontWeight: 500 }}>
              Credit Risk &amp; Fraud-Resilient Loan Underwriting Station
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
