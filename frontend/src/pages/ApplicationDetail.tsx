import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { applications, documents, auditLog } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip
} from 'recharts'
import {
  ArrowLeft, CheckCircle2, XCircle, AlertTriangle, Minus,
  ShieldCheck, FileText, GitMerge, ClipboardCheck, BookOpen, Lock, Activity, RefreshCw
} from 'lucide-react'

const formatINR = (n: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)

function ScoreBar({ score, label }: { score: number; label: string }) {
  const cls = score >= 90 ? 'score-bar-pass' : score >= 70 ? 'score-bar-review' : 'score-bar-risk'
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontWeight: 700 }}>{score.toFixed(1)}</span>
      </div>
      <div className="score-bar-track">
        <div className={`score-bar-fill ${cls}`} style={{ width: `${score}%` }} />
      </div>
    </div>
  )
}

function MatchIcon({ status }: { status: string }) {
  if (status === 'MATCH') return <CheckCircle2 size={14} className="match-match" />
  if (status === 'SOFT_MATCH') return <AlertTriangle size={14} className="match-soft" />
  if (status === 'MISMATCH') return <XCircle size={14} className="match-mismatch" />
  if (status === 'PARTIAL') return <Minus size={14} className="match-partial" />
  return <Minus size={14} className="match-skipped" />
}

export default function ApplicationDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<any>(null)
  const [tab, setTab] = useState('overview')
  const [decision, setDecision] = useState('')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [chainStatus, setChainStatus] = useState<any>(null)
  const [auditEntries, setAuditEntries] = useState<any[]>([])

  const [reanalyzing, setReanalyzing] = useState(false)

  const loadData = async () => {
    if (!id) return
    try {
      const [dashRes, auditRes] = await Promise.all([
        applications.dashboard(id),
        auditLog.list(id)
      ])
      setData(dashRes.data)
      setAuditEntries(auditRes.data)
      return dashRes.data
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    if (!id) return
    let timer: any
    let active = true

    const poll = async () => {
      const current = await loadData()
      if (active && (current?.application?.status === 'ANALYZING' || current?.application?.status === 'PENDING' || !current?.risk_score)) {
        timer = setTimeout(poll, 2000)
      }
    }

    poll()

    return () => {
      active = false
      if (timer) clearTimeout(timer)
    }
  }, [id])

  const triggerReanalysis = async () => {
    if (!data?.documents?.length) return
    setReanalyzing(true)
    for (const doc of data.documents) {
      try {
        await documents.analyze(doc.id)
      } catch (e) {
        console.error(e)
      }
    }
    await loadData()
    setReanalyzing(false)
  }

  const submitReview = async () => {
    if (!decision || !id) return
    setSubmitting(true)
    await applications.review(id, { decision, notes })
    await loadData()
    setSubmitting(false)
  }

  const verifyChain = async () => {
    const r = await auditLog.verify()
    setChainStatus(r.data)
  }

  if (!data) return (
    <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 80 }}>
      <div className="spinner" />
    </div>
  )

  const { application: app, risk_score: risk, field_comparisons, rule_checks, cross_doc_checks, tamper_signals } = data
  const status = risk?.status ?? app.status

  const radarData = risk ? [
    { metric: 'Agreement', score: risk.agreement_score },
    { metric: 'Consistency', score: risk.consistency_score },
    { metric: 'Tamper', score: risk.tamper_score },
    { metric: 'Confidence', score: risk.confidence_score },
  ] : []

  return (
    <div className="fade-in">
      {/* Header Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <button className="btn btn-ghost" onClick={() => navigate('/')} style={{ padding: '8px 14px' }}>
          <ArrowLeft size={14} /> Back
        </button>
        <button
          className="btn btn-primary"
          onClick={triggerReanalysis}
          disabled={reanalyzing || !data?.documents?.length}
          style={{ padding: '8px 16px', fontSize: 13 }}
        >
          <RefreshCw size={14} className={reanalyzing ? 'spinner' : ''} style={{ display: 'inline', marginRight: 6 }} />
          {reanalyzing ? 'Verifying AI Pipelines...' : 'Re-run Dual-AI Verification'}
        </button>
      </div>

      {app.is_synthetic && (
        <div className="synthetic-banner">
          ⚠️ SYNTHETIC DATA — NOT A REAL APPLICANT — FOR DEMONSTRATION PURPOSES ONLY
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
        <div>
          <h1 className="page-title">{app.applicant_name}</h1>
          <div style={{ color: 'var(--text-secondary)', fontSize: 14, marginTop: 4 }}>
            {app.loan_type.charAt(0).toUpperCase() + app.loan_type.slice(1)} Loan ·{' '}
            <strong style={{ color: 'var(--text-primary)' }}>{formatINR(app.loan_amount)}</strong>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {risk && (
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 32, fontWeight: 800, letterSpacing: -1,
                color: status === 'PASS' ? 'var(--pass)' : status === 'REVIEW' ? 'var(--review)' : 'var(--risk)' }}>
                {risk.overall_score.toFixed(0)}<span style={{ fontSize: 18, opacity: 0.6 }}>/100</span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Risk Score</div>
            </div>
          )}
          <StatusBadge status={status} />
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        {[
          { id: 'overview', label: 'Overview', Icon: ShieldCheck },
          { id: 'fields', label: 'Field Comparison', Icon: GitMerge },
          { id: 'rules', label: 'Rule Engine', Icon: ClipboardCheck },
          { id: 'crossdoc', label: 'Cross-Document', Icon: FileText },
          { id: 'audit', label: 'Audit Log', Icon: BookOpen },
        ].map(({ id: tid, label, Icon }) => (
          <button key={tid} className={`tab-btn ${tab === tid ? 'active' : ''}`} onClick={() => setTab(tid)}>
            <Icon size={13} style={{ display: 'inline', marginRight: 6 }} />{label}
          </button>
        ))}
      </div>

      {/* OVERVIEW TAB */}
      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {/* Explainability */}
          {risk?.explanation_text && (
            <div className="explain-card" style={{ gridColumn: '1 / -1' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <ShieldCheck size={16} style={{ color: 'var(--accent-bright)' }} />
                <span style={{ fontWeight: 700, fontSize: 14 }}>Why This Was Flagged</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 4 }}>Generated by AI — for reviewer context only</span>
              </div>
              <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 14 }}>
                {risk.explanation_text}
              </p>
            </div>
          )}

          {/* Score breakdown */}
          {risk && (
            <div className="card">
              <div style={{ fontWeight: 700, marginBottom: 20 }}>Score Breakdown</div>
              <ScoreBar score={risk.agreement_score} label="AI Pipeline Agreement" />
              <ScoreBar score={risk.consistency_score} label="Cross-Document Consistency" />
              <ScoreBar score={risk.tamper_score} label="Tamper & Rule Signals" />
              <ScoreBar score={risk.confidence_score} label="Model Confidence" />
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16, marginTop: 4 }}>
                <ScoreBar score={risk.overall_score} label="Overall Score" />
              </div>
              {risk.single_source && (
                <div style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 8, padding: '8px 12px', fontSize: 12, color: 'var(--review)', marginTop: 12 }}>
                  ⚠️ Single-source analysis — one AI pipeline failed. Score capped.
                </div>
              )}
            </div>
          )}

          {/* Radar chart */}
          {radarData.length > 0 && (
            <div className="card">
              <div style={{ fontWeight: 700, marginBottom: 12 }}>Score Radar</div>
              <ResponsiveContainer width="100%" height={220}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="var(--border)" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                  <Radar name="Score" dataKey="score" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.15} strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Tamper signals */}
          {tamper_signals?.length > 0 && (
            <div className="card" style={{ gridColumn: '1 / -1' }}>
              <div style={{ fontWeight: 700, marginBottom: 12 }}>🔴 Tamper Signals Detected</div>
              {tamper_signals.map((sig: any, i: number) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
                  <XCircle size={14} style={{ color: 'var(--risk)' }} />
                  <span style={{ color: 'var(--text-secondary)' }}>{sig.detail}</span>
                  <span className="badge badge-risk" style={{ marginLeft: 'auto' }}>{sig.severity}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* FIELD COMPARISON TAB */}
      {tab === 'fields' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
            <GitMerge size={16} style={{ color: 'var(--accent-bright)' }} />
            <span style={{ fontWeight: 700 }}>Field-by-Field Pipeline Comparison</span>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Groq (AI-A)</th>
                <th>Mistral (AI-B)</th>
                <th>Match</th>
                <th>Weight</th>
              </tr>
            </thead>
            <tbody>
              {field_comparisons?.map((f: any, i: number) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600, fontFamily: 'monospace', fontSize: 13 }}>{f.field_name}</td>
                  <td style={{ fontSize: 13 }}>{f.groq_value ?? <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>null</span>}</td>
                  <td style={{ fontSize: 13 }}>{f.mistral_value ?? <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>null</span>}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <MatchIcon status={f.match_status} />
                      <span style={{ fontSize: 12 }} className={`match-${f.match_status.toLowerCase().replace('_match','').replace('soft','soft')}`}>
                        {f.match_status}
                      </span>
                    </div>
                  </td>
                  <td style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{f.weight}×</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* RULE ENGINE TAB */}
      {tab === 'rules' && (
        <div>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 10 }}>
              <ClipboardCheck size={16} style={{ color: 'var(--accent-bright)' }} />
              <span style={{ fontWeight: 700 }}>Deterministic Rule Engine</span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 4 }}>
                AI-independent checks — catches fraud even if both AIs are fooled
              </span>
            </div>
            <table className="table">
              <thead>
                <tr><th>Rule</th><th>Status</th><th>Severity</th><th>Detail</th></tr>
              </thead>
              <tbody>
                {rule_checks?.map((r: any, i: number) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600, fontFamily: 'monospace', fontSize: 13 }}>{r.rule_name}</td>
                    <td>
                      {r.passed
                        ? <span className="badge badge-pass"><CheckCircle2 size={11} /> Pass</span>
                        : <span className={r.severity === 'HIGH_RISK' ? 'badge badge-risk' : 'badge badge-review'}>
                            <XCircle size={11} /> Fail
                          </span>
                      }
                    </td>
                    <td>
                      <span className={`badge ${r.severity === 'HIGH_RISK' ? 'badge-risk' : 'badge-review'}`}>
                        {r.severity}
                      </span>
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{r.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CROSS-DOC TAB */}
      {tab === 'crossdoc' && (
        <div style={{ display: 'grid', gap: 12 }}>
          {cross_doc_checks?.map((c: any, i: number) => (
            <div key={i} className="card card-sm" style={{
              border: `1px solid ${c.result === 'OK' ? 'var(--pass-border)' : 'var(--risk-border)'}`,
              background: c.result === 'OK' ? 'var(--pass-bg)' : 'var(--risk-bg)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13, fontFamily: 'monospace', marginBottom: 4 }}>
                    {c.check_type}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{c.detail}</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                  <span className={`badge ${c.result === 'OK' ? 'badge-pass' : 'badge-risk'}`}>
                    {c.result}
                  </span>
                  {c.discrepancy_pct && (
                    <span style={{ fontSize: 12, color: 'var(--risk)', fontWeight: 700 }}>
                      {c.discrepancy_pct.toFixed(1)}% gap
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
          {(!cross_doc_checks || cross_doc_checks.length === 0) && (
            <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
              No cross-document checks available (only one document uploaded).
            </div>
          )}
        </div>
      )}

      {/* AUDIT LOG TAB */}
      {tab === 'audit' && (
        <div>
          <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
            <button className="btn btn-ghost" onClick={verifyChain} style={{ fontSize: 13 }}>
              <Lock size={14} /> Verify Hash Chain
            </button>
            {chainStatus && (
              <div className={`badge ${chainStatus.chain_valid ? 'badge-pass' : 'badge-risk'}`} style={{ alignItems: 'center' }}>
                {chainStatus.chain_valid ? '✓ Chain Valid' : '✗ Chain BROKEN'} · {chainStatus.total_entries} entries
              </div>
            )}
          </div>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="table">
              <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Entry Hash</th></tr></thead>
              <tbody>
                {auditEntries.map((e: any, i: number) => (
                  <tr key={i}>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                      {new Date(e.created_at).toLocaleString('en-IN')}
                    </td>
                    <td style={{ fontSize: 13 }}>{e.actor}</td>
                    <td style={{ fontSize: 13, fontFamily: 'monospace' }}>{e.action}</td>
                    <td style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-muted)' }}>
                      {e.entry_hash.slice(0, 16)}...
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* DECISION PANEL — sticky footer */}
      {app.status !== 'decided' && (
        <div style={{
          position: 'sticky', bottom: 24, marginTop: 32,
          background: 'var(--bg-card)',
          border: '1px solid var(--border-bright)',
          borderRadius: 12, padding: 20,
          boxShadow: '0 -4px 24px rgba(0,0,0,0.5)',
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 20 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>Record Human Review Decision</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
                This system does not make automated approve/reject decisions. Your decision is final.
              </div>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Reviewer notes (optional)..."
                style={{
                  width: '100%', background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                  borderRadius: 8, padding: 10, color: 'var(--text-primary)', fontSize: 13,
                  resize: 'vertical', minHeight: 60, fontFamily: 'inherit',
                }}
              />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 200 }}>
              {[
                { value: 'approve_for_underwriting', label: '✓ Approve for Underwriting', cls: 'btn-pass' },
                { value: 'request_more_documents', label: '⊕ Request More Documents', cls: 'btn-ghost' },
                { value: 'reject', label: '✗ Reject', cls: 'btn-risk' },
              ].map(({ value, label, cls }) => (
                <button
                  key={value}
                  className={`btn ${cls} ${decision === value ? 'btn-primary' : ''}`}
                  onClick={() => setDecision(value)}
                  style={{ justifyContent: 'flex-start', fontSize: 13 }}
                >
                  {label}
                </button>
              ))}
              <button
                className="btn btn-primary"
                onClick={submitReview}
                disabled={!decision || submitting}
                style={{ marginTop: 4 }}
              >
                {submitting ? 'Saving...' : 'Submit Decision →'}
              </button>
            </div>
          </div>
        </div>
      )}

      {app.status === 'decided' && (
        <div className="card" style={{ marginTop: 24, border: '1px solid rgba(139,92,246,0.3)', background: 'rgba(139,92,246,0.05)' }}>
          <div style={{ color: '#a78bfa', fontWeight: 700 }}>✓ Review Completed</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 13, marginTop: 4 }}>
            A human reviewer has recorded a decision for this application.
          </div>
        </div>
      )}
    </div>
  )
}
