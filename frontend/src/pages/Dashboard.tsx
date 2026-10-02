import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { applications } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import { ChevronRight, CheckCircle2, AlertTriangle, AlertOctagon, Plus, Search, Filter, ShieldCheck, Building2 } from 'lucide-react'

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
  const [searchTerm, setSearchTerm] = useState('')
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

  const filteredApps = apps.filter(a => 
    a.applicant_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    a.loan_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
    a.id.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="fade-in">
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16, marginBottom: 24 }}>
        <div>
          <h1 className="page-title">Commercial Credit Underwriting Queue</h1>
          <p className="page-subtitle">
            Dual-AI verified loan origination files awaiting credit officer review and risk sanctioning
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button className="btn btn-accent" onClick={() => navigate('/new')}>
            <Plus size={15} /> New Loan Dossier
          </button>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="stat-grid">
        <div className="stat-card stat-primary">
          <div className="stat-value mono" style={{ color: 'var(--bank-navy)' }}>{total}</div>
          <div className="stat-label">Total Files in Queue</div>
        </div>
        <div className="stat-card stat-pass">
          <div className="stat-value mono" style={{ color: 'var(--risk-pass-bar)' }}>{passes}</div>
          <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <CheckCircle2 size={12} color="var(--risk-pass-bar)" />
            Passed Underwriting (&ge;90)
          </div>
        </div>
        <div className="stat-card stat-review">
          <div className="stat-value mono" style={{ color: 'var(--risk-review-bar)' }}>{reviews}</div>
          <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <AlertTriangle size={12} color="var(--risk-review-bar)" />
            Discrepancy Review (70–89)
          </div>
        </div>
        <div className="stat-card stat-risk">
          <div className="stat-value mono" style={{ color: 'var(--risk-fail-bar)' }}>{highRisk}</div>
          <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <AlertOctagon size={12} color="var(--risk-fail-bar)" />
            High Risk / Tamper (&lt;70)
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card" style={{ padding: '12px 16px', marginBottom: 18 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          {/* Segmented Filter Buttons */}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {[
              { label: 'All Files', val: '' },
              { label: 'Low Risk (≥90)', val: 'PASS' },
              { label: 'Manual Review (70–89)', val: 'REVIEW' },
              { label: 'High Risk (<70)', val: 'HIGH_RISK_REVIEW' },
              { label: 'Decided Files', val: 'DECIDED' },
            ].map(s => (
              <button
                key={s.val}
                onClick={() => setFilter(s.val)}
                className={`btn ${filter === s.val ? 'btn-primary' : 'btn-ghost'}`}
                style={{ padding: '6px 14px', fontSize: '12.5px' }}
              >
                {s.label}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <div style={{ position: 'relative', minWidth: 260 }}>
            <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--bank-text-muted)' }} />
            <input
              type="text"
              placeholder="Search applicant name, ID, facility..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              style={{ width: '100%', paddingLeft: 32, fontSize: 13, height: 34 }}
            />
          </div>
        </div>
      </div>

      {/* Enterprise Data Grid */}
      <div className="table-container">
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48, gap: 12 }}>
            <div className="spinner" />
            <div style={{ fontSize: 13, color: 'var(--bank-text-muted)' }}>Retrieving underwriting ledger...</div>
          </div>
        ) : filteredApps.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 48, color: 'var(--bank-text-muted)' }}>
            No credit files matching the selected criteria.
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: '28%' }}>Applicant &amp; Dossier ID</th>
                <th style={{ width: '18%' }}>Facility Type</th>
                <th style={{ width: '18%' }}>Sanction Request</th>
                <th style={{ width: '18%' }}>Risk Classification</th>
                <th style={{ width: '12%' }}>Submission Date</th>
                <th style={{ width: '6%', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredApps.map(app => (
                <tr
                  key={app.id}
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/applications/${app.id}`)}
                >
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--bank-navy)' }}>{app.applicant_name}</div>
                    <div className="mono" style={{ fontSize: 11, color: 'var(--bank-text-muted)', marginTop: 2 }}>
                      REF: {app.id.slice(0, 12)}...
                    </div>
                  </td>
                  <td>
                    <span style={{
                      textTransform: 'capitalize',
                      fontWeight: 500,
                      background: 'var(--bank-canvas)',
                      padding: '3px 8px',
                      borderRadius: 4,
                      border: '1px solid var(--bank-border)',
                      fontSize: 12
                    }}>
                      {app.loan_type} Loan
                    </span>
                  </td>
                  <td>
                    <span className="mono" style={{ fontWeight: 600, color: 'var(--bank-text-main)', fontSize: 13.5 }}>
                      {formatCurrency(app.loan_amount)}
                    </span>
                  </td>
                  <td>
                    <StatusBadge status={app.status} />
                  </td>
                  <td>
                    <span className="mono" style={{ fontSize: 12.5, color: 'var(--bank-text-secondary)' }}>
                      {formatDate(app.created_at)}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--bank-blue)', fontWeight: 600, fontSize: 12 }}>
                      <span>Review</span>
                      <ChevronRight size={14} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Compliance Regulatory Footnote */}
      <div style={{ marginTop: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11.5, color: 'var(--bank-text-muted)' }}>
        <div>
          Institutional Guidance: Scoring engine provides algorithmic consensus routing. Final loan sanctioning remains subject to accredited credit authority sign-off.
        </div>
        <div className="mono">
          DUALTRUST CORE 2.4.0
        </div>
      </div>
    </div>
  )
}
