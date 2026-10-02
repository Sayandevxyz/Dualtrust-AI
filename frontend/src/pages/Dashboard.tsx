import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { applications } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import { ChevronRight, TrendingUp, AlertTriangle, CheckCircle, Clock } from 'lucide-react'

interface Application {
  id: string
  applicant_name: string
  loan_type: string
  loan_amount: number
  status: string
  created_at: string
}

function formatCurrency(n: number) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)
}

function formatDate(s: string) {
  return new Date(s).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function Dashboard() {
  const [apps, setApps] = useState<Application[]>([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const fetchApps = () => {
    applications.list(filter || undefined).then(r => {
      setApps(r.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchApps()
    const interval = setInterval(fetchApps, 4000)
    return () => clearInterval(interval)
  }, [filter])

  const total = apps.length
  const passes = apps.filter(a => (a.status || '').toUpperCase() === 'PASS').length
  const reviews = apps.filter(a => (a.status || '').toUpperCase() === 'REVIEW').length
  const highRisk = apps.filter(a => (a.status || '').toUpperCase() === 'HIGH_RISK_REVIEW').length
  const pending = apps.filter(a => ['PENDING', 'ANALYZING'].includes((a.status || '').toUpperCase())).length

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12, marginBottom: 20 }}>
        <div>
          <h1 className="page-title">Verification Dashboard</h1>
          <p className="page-subtitle">AI-assisted routing only — all decisions require human review</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <div style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.25)', borderRadius: 20, padding: '4px 12px', fontSize: 12, color: 'var(--accent-bright)', fontWeight: 600 }}>
            ⚡ Team: Destroyers X
          </div>
          <button className="btn btn-primary" onClick={() => navigate('/new')} style={{ padding: '8px 16px', fontSize: 13 }}>
            + New Application
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--accent-bright)' }}>{total}</div>
          <div className="stat-label">Total Applications</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--pass)' }}>{passes}</div>
          <div className="stat-label">
            <CheckCircle size={12} style={{ display: 'inline', marginRight: 4 }} />
            Passed (&ge;90)
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--review)' }}>{reviews}</div>
          <div className="stat-label">
            <AlertTriangle size={12} style={{ display: 'inline', marginRight: 4 }} />
            Needs Review (70-89)
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--risk)' }}>{highRisk}</div>
          <div className="stat-label">
            High Risk (&lt;70)
          </div>
        </div>
      </div>

      {/* Filter bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {[
          { label: 'All', val: '' },
          { label: 'Pass (>=90)', val: 'PASS' },
          { label: 'Review (70-89)', val: 'REVIEW' },
          { label: 'High Risk (<70)', val: 'HIGH_RISK_REVIEW' },
          { label: 'Decided', val: 'DECIDED' },
        ].map(s => (
          <button
            key={s.val}
            onClick={() => setFilter(s.val)}
            className={`btn ${filter === s.val ? 'btn-primary' : 'btn-ghost'}`}
            style={{ padding: '8px 16px', fontSize: 13 }}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
            <div className="spinner" />
          </div>
        ) : apps.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>
            No applications found. <a href="/new" style={{ color: 'var(--accent-bright)' }}>Create one</a>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Applicant</th>
                <th>Loan Type</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Submitted</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {apps.map(app => (
                <tr key={app.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/applications/${app.id}`)}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{app.applicant_name}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{app.id.slice(0, 8)}...</div>
                  </td>
                  <td style={{ textTransform: 'capitalize' }}>{app.loan_type}</td>
                  <td style={{ fontWeight: 600 }}>{formatCurrency(app.loan_amount)}</td>
                  <td><StatusBadge status={app.status} /></td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{formatDate(app.created_at)}</td>
                  <td><ChevronRight size={16} style={{ color: 'var(--text-muted)' }} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
