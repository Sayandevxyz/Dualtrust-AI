import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { applications, documents, auditLog } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer
} from 'recharts'
import {
  ArrowLeft, CheckCircle2, XCircle, AlertTriangle, Minus,
  ShieldCheck, FileText, GitMerge, ClipboardCheck, BookOpen, Lock, Activity, RefreshCw,
  Building, UserCheck, Scale, FileSpreadsheet, AlertOctagon
} from 'lucide-react'

const formatINR = (n: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)

function ScoreBar({ score, label }: { score: number; label: string }) {
  const cls = score >= 90 ? 'score-bar-pass' : score >= 70 ? 'score-bar-review' : 'score-bar-risk'
  const textColor = score >= 90 ? 'var(--risk-pass-bar)' : score >= 70 ? 'var(--risk-review-bar)' : 'var(--risk-fail-bar)'
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
        <span style={{ color: 'var(--bank-text-secondary)', fontWeight: 500 }}>{label}</span>
        <span className="mono" style={{ fontWeight: 700, color: textColor }}>{score.toFixed(1)}%</span>
      </div>
      <div className="score-bar-track">
        <div className={`score-bar-fill ${cls}`} style={{ width: `${Math.min(100, Math.max(0, score))}%` }} />
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
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', paddingTop: 80, gap: 14 }}>
      <div className="spinner" />
      <div style={{ fontSize: 13, color: 'var(--bank-text-muted)' }}>Loading credit file &amp; risk models...</div>
    </div>
  )

  const { application: app, risk_score: risk, field_comparisons, rule_checks, cross_doc_checks, tamper_signals } = data
  const status = risk?.status ?? app.status

  const radarData = risk ? [
    { metric: 'Agreement', score: risk.agreement_score },
    { metric: 'Consistency', score: risk.consistency_score },
    { metric: 'Tamper-Free', score: risk.tamper_score },
    { metric: 'Confidence', score: risk.confidence_score },
  ] : []

  return (
    <div className="fade-in">
      {/* Top Breadcrumb & Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <button className="btn btn-ghost" onClick={() => navigate('/')} style={{ fontSize: 13 }}>
          <ArrowLeft size={14} /> Back to Underwriting Queue
        </button>
        <button
          className="btn btn-accent"
          onClick={triggerReanalysis}
          disabled={reanalyzing || !data?.documents?.length}
        >
          <RefreshCw size={14} className={reanalyzing ? 'spinner' : ''} />
          {reanalyzing ? 'Running Dual-AI Verification...' : 'Re-run Consensus Verification'}
        </button>
      </div>

      {app.is_synthetic && (
        <div className="bank-alert-banner">
          <AlertTriangle size={16} />
          <div>
            <strong>SYNTHETIC COMPLIANCE DATASET</strong>: This file contains synthetic test borrower documentation for underwriting audit simulations.
          </div>
        </div>
      )}

      {/* Credit File Main Header Card */}
      <div className="card" style={{ marginBottom: 20, borderLeft: '4px solid var(--bank-navy)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span className="mono" style={{ fontSize: 11, fontWeight: 700, color: 'var(--bank-text-muted)', background: 'var(--bank-canvas)', padding: '2px 8px', borderRadius: 4, border: '1px solid var(--bank-border)' }}>
                FILE REF: {app.id.slice(0, 16)}
              </span>
              <span style={{ fontSize: 12, color: 'var(--bank-text-muted)' }}>Filed: {new Date(app.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</span>
            </div>
            <h1 className="page-title" style={{ fontSize: 24, marginBottom: 4 }}>{app.applicant_name}</h1>
            <div style={{ color: 'var(--bank-text-secondary)', fontSize: 14 }}>
              Facility: <strong style={{ color: 'var(--bank-navy)' }}>{app.loan_type.toUpperCase()} LOAN</strong> · Sanction Amount:{' '}
              <strong className="mono" style={{ color: 'var(--bank-navy)', fontSize: 16 }}>{formatINR(app.loan_amount)}</strong>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16, background: 'var(--bank-surface-muted)', padding: '12px 18px', borderRadius: 6, border: '1px solid var(--bank-border)' }}>
            {risk && (
              <div style={{ textAlign: 'right' }}>
                <div className="mono" style={{
                  fontSize: 28, fontWeight: 700, lineHeight: 1.1,
                  color: status === 'PASS' ? 'var(--risk-pass-bar)' : status === 'REVIEW' ? 'var(--risk-review-bar)' : 'var(--risk-fail-bar)'
                }}>
                  {risk.overall_score.toFixed(0)}<span style={{ fontSize: 15, color: 'var(--bank-text-muted)' }}>/100</span>
                </div>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--bank-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Risk Index
                </div>
              </div>
            )}
            <StatusBadge status={status} />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        {[
          { id: 'overview', label: 'Credit Risk Overview', Icon: ShieldCheck },
          { id: 'fields', label: 'Field Reconciliation', Icon: GitMerge },
          { id: 'rules', label: 'Underwriting Rule Engine', Icon: ClipboardCheck },
          { id: 'crossdoc', label: 'Cross-Document Audit', Icon: FileText },
          { id: 'audit', label: 'Cryptographic Audit Trail', Icon: BookOpen },
        ].map(({ id: tid, label, Icon }) => (
          <button key={tid} className={`tab-btn ${tab === tid ? 'active' : ''}`} onClick={() => setTab(tid)}>
            <Icon size={14} />{label}
          </button>
        ))}
      </div>

      {/* OVERVIEW TAB */}
      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 20 }}>
          {/* Executive Risk Memorandum */}
          {risk?.explanation_text && (
            <div className="card" style={{ gridColumn: '1 / -1', borderLeft: '4px solid #0056b3' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                <Scale size={16} color="var(--bank-blue)" />
                <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--bank-navy)' }}>
                  Underwriter Risk Memorandum &amp; Automated Audit Finding
                </span>
                <span style={{ fontSize: 11, color: 'var(--bank-text-muted)', marginLeft: 'auto' }}>
                  Standard Underwriting Guideline 8.1
                </span>
              </div>
              <p style={{ color: 'var(--bank-text-secondary)', lineHeight: 1.7, fontSize: 13.5, background: 'var(--bank-surface-muted)', padding: 14, borderRadius: 6, border: '1px solid var(--bank-border)' }}>
                {risk.explanation_text}
              </p>
            </div>
          )}

          {/* Quantitative Score Breakdown */}
          {risk && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">Consensus Scoring Components</span>
                <span className="mono" style={{ fontSize: 11, color: 'var(--bank-text-muted)' }}>WEIGHTED EVALUATION</span>
              </div>
              <ScoreBar score={risk.agreement_score} label="Dual-AI Extraction Agreement (Groq vs Mistral)" />
              <ScoreBar score={risk.consistency_score} label="Cross-Document Cross-Referencing" />
              <ScoreBar score={risk.tamper_score} label="Document Integrity & Signal Analysis" />
              <ScoreBar score={risk.confidence_score} label="Model Extraction Confidence" />
              
              <div style={{ borderTop: '2px solid var(--bank-border)', paddingTop: 14, marginTop: 10 }}>
                <ScoreBar score={risk.overall_score} label="Final Composite Risk Index" />
              </div>

              {risk.single_source && (
                <div className="bank-alert-banner" style={{ marginTop: 14 }}>
                  <AlertTriangle size={15} />
                  <span>Single-source fallback: One pipeline failed. Score capped at maximum 70.0 for safety.</span>
                </div>
              )}
            </div>
          )}

          {/* Radar Chart */}
          {radarData.length > 0 && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">Risk Dimension Profile</span>
                <span style={{ fontSize: 11, color: 'var(--bank-text-muted)' }}>4-AXIS RADAR</span>
              </div>
              <ResponsiveContainer width="100%" height={240}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: '#475569', fontSize: 11, fontWeight: 500 }} />
                  <Radar name="Score" dataKey="score" stroke="#0056b3" fill="#0056b3" fillOpacity={0.15} strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Tamper Signals */}
          {tamper_signals?.length > 0 && (
            <div className="card" style={{ gridColumn: '1 / -1', borderLeft: '4px solid var(--risk-fail-bar)' }}>
              <div className="card-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <AlertOctagon size={16} color="var(--risk-fail-bar)" />
                  <span className="card-title" style={{ color: 'var(--risk-fail-text)' }}>
                    Physical &amp; Digital Document Anomalies Detected ({tamper_signals.length})
                  </span>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {tamper_signals.map((sig: any, i: number) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--risk-fail-bg)', border: '1px solid var(--risk-fail-border)', borderRadius: 5 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <XCircle size={15} color="var(--risk-fail-bar)" />
                      <span style={{ fontSize: 13, color: 'var(--risk-fail-text)', fontWeight: 500 }}>{sig.detail}</span>
                    </div>
                    <span className="badge badge-risk">{sig.severity}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* FIELD COMPARISON TAB */}
      {tab === 'fields' && (
        <div className="table-container">
          <div style={{ padding: '14px 18px', background: 'var(--bank-surface-muted)', borderBottom: '1px solid var(--bank-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <GitMerge size={16} color="var(--bank-navy)" />
              <span style={{ fontWeight: 700, color: 'var(--bank-navy)', fontSize: 14 }}>
                Dual-AI Pipeline Field Extraction &amp; Reconciliation Matrix
              </span>
            </div>
            <span style={{ fontSize: 12, color: 'var(--bank-text-muted)' }}>
              Independent consensus between Groq Llama-3 &amp; Mistral Large
            </span>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: '25%' }}>Attribute / Field Key</th>
                <th style={{ width: '25%' }}>Pipeline A (Groq Extraction)</th>
                <th style={{ width: '25%' }}>Pipeline B (Mistral Extraction)</th>
                <th style={{ width: '15%' }}>Consensus Status</th>
                <th style={{ width: '10%', textAlign: 'right' }}>Weight</th>
              </tr>
            </thead>
            <tbody>
              {field_comparisons?.map((f: any, i: number) => (
                <tr key={i}>
                  <td>
                    <span className="mono" style={{ fontWeight: 600, color: 'var(--bank-navy)', fontSize: 12.5 }}>
                      {f.field_name}
                    </span>
                  </td>
                  <td style={{ fontSize: 13, color: 'var(--bank-text-main)' }}>
                    {f.groq_value ?? <span style={{ color: 'var(--bank-text-muted)', fontStyle: 'italic' }}>—</span>}
                  </td>
                  <td style={{ fontSize: 13, color: 'var(--bank-text-main)' }}>
                    {f.mistral_value ?? <span style={{ color: 'var(--bank-text-muted)', fontStyle: 'italic' }}>—</span>}
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <MatchIcon status={f.match_status} />
                      <span style={{ fontSize: 12 }} className={`match-${f.match_status.toLowerCase().replace('_match','').replace('soft','soft')}`}>
                        {f.match_status.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </td>
                  <td style={{ textAlign: 'right', fontWeight: 600, color: 'var(--bank-text-muted)', fontSize: 12.5 }}>
                    {f.weight}×
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* RULE ENGINE TAB */}
      {tab === 'rules' && (
        <div className="table-container">
          <div style={{ padding: '14px 18px', background: 'var(--bank-surface-muted)', borderBottom: '1px solid var(--bank-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <ClipboardCheck size={16} color="var(--bank-navy)" />
              <span style={{ fontWeight: 700, color: 'var(--bank-navy)', fontSize: 14 }}>
                Deterministic Credit Policy &amp; Regulatory Checks
              </span>
            </div>
            <span style={{ fontSize: 12, color: 'var(--bank-text-muted)' }}>
              Deterministic verification rules executed independently of generative models
            </span>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: '25%' }}>Rule Code / Check</th>
                <th style={{ width: '15%' }}>Compliance Result</th>
                <th style={{ width: '15%' }}>Severity Tier</th>
                <th style={{ width: '45%' }}>Audit Detail &amp; Finding</th>
              </tr>
            </thead>
            <tbody>
              {rule_checks?.map((r: any, i: number) => (
                <tr key={i}>
                  <td>
                    <span className="mono" style={{ fontWeight: 600, color: 'var(--bank-navy)', fontSize: 12.5 }}>
                      {r.rule_name}
                    </span>
                  </td>
                  <td>
                    {r.passed
                      ? <span className="badge badge-pass"><CheckCircle2 size={11} /> Pass</span>
                      : <span className={r.severity === 'HIGH_RISK' ? 'badge badge-risk' : 'badge badge-review'}>
                          <XCircle size={11} /> Non-Compliant
                        </span>
                    }
                  </td>
                  <td>
                    <span className={`badge ${r.severity === 'HIGH_RISK' ? 'badge-risk' : 'badge-review'}`}>
                      {r.severity.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td style={{ fontSize: 13, color: 'var(--bank-text-secondary)' }}>{r.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* CROSS-DOC TAB */}
      {tab === 'crossdoc' && (
        <div style={{ display: 'grid', gap: 12 }}>
          {cross_doc_checks?.map((c: any, i: number) => (
            <div key={i} className="card card-sm" style={{
              borderLeft: `4px solid ${c.result === 'OK' ? 'var(--risk-pass-bar)' : 'var(--risk-fail-bar)'}`,
              background: '#ffffff'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div className="mono" style={{ fontWeight: 700, fontSize: 13, color: 'var(--bank-navy)', marginBottom: 4 }}>
                    {c.check_type.replace(/_/g, ' ')}
                  </div>
                  <div style={{ fontSize: 13.5, color: 'var(--bank-text-secondary)' }}>{c.detail}</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                  <span className={`badge ${c.result === 'OK' ? 'badge-pass' : 'badge-risk'}`}>
                    {c.result === 'OK' ? 'Reconciled' : 'Discrepancy'}
                  </span>
                  {c.discrepancy_pct && (
                    <span className="mono" style={{ fontSize: 12, color: 'var(--risk-fail-bar)', fontWeight: 700 }}>
                      Δ {c.discrepancy_pct.toFixed(1)}% variance
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
          {(!cross_doc_checks || cross_doc_checks.length === 0) && (
            <div className="card" style={{ textAlign: 'center', padding: 36, color: 'var(--bank-text-muted)' }}>
              Single document present in dossier — cross-document multi-instrument reconciliation requires at least 2 instruments.
            </div>
          )}
        </div>
      )}

      {/* AUDIT LOG TAB */}
      {tab === 'audit' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <button className="btn btn-ghost" onClick={verifyChain} style={{ fontSize: 13 }}>
                <Lock size={14} /> Validate SHA-256 Ledger Integrity
              </button>
              {chainStatus && (
                <div className={`badge ${chainStatus.chain_valid ? 'badge-pass' : 'badge-risk'}`}>
                  {chainStatus.chain_valid ? '✓ Chain Cryptographically Verified' : '✗ Tampering Detected in Chain'} · {chainStatus.total_entries} entries
                </div>
              )}
            </div>
            <span style={{ fontSize: 11, color: 'var(--bank-text-muted)' }}>
              Append-only tamper-evident audit ledger
            </span>
          </div>

          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: '20%' }}>Timestamp (IST)</th>
                  <th style={{ width: '20%' }}>Operator / Entity</th>
                  <th style={{ width: '30%' }}>Underwriting Event</th>
                  <th style={{ width: '30%' }}>Merkle / Entry Hash</th>
                </tr>
              </thead>
              <tbody>
                {auditEntries.map((e: any, i: number) => (
                  <tr key={i}>
                    <td className="mono" style={{ fontSize: 12, color: 'var(--bank-text-secondary)', whiteSpace: 'nowrap' }}>
                      {new Date(e.created_at).toLocaleString('en-IN')}
                    </td>
                    <td style={{ fontSize: 13, fontWeight: 600, color: 'var(--bank-navy)' }}>{e.actor}</td>
                    <td style={{ fontSize: 13 }}>{e.action}</td>
                    <td className="mono" style={{ fontSize: 11, color: 'var(--bank-text-muted)' }}>
                      {e.entry_hash}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* DECISION SIGN-OFF PANEL — Institutional Sticky Footer */}
      {app.status !== 'decided' && (
        <div style={{
          position: 'sticky', bottom: 20, marginTop: 32,
          background: 'var(--bank-navy)',
          color: '#ffffff',
          borderRadius: 8, padding: 20,
          boxShadow: '0 8px 30px rgba(15,23,42,0.25)',
          border: '1px solid #1a2a40'
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 24 }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <UserCheck size={16} color="#60a5fa" />
                <span style={{ fontWeight: 700, fontSize: 15, color: '#ffffff' }}>
                  Accredited Underwriting Officer Sign-Off &amp; Sanction Note
                </span>
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 12 }}>
                Statutory Requirement: Underwriting officer must record deliberate rationales before issuing credit commitment or referring to FIU.
              </div>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Enter credit memorandum, underwriting rationale, or exception reason..."
                style={{
                  width: '100%', background: '#091524', border: '1px solid #254b7a',
                  borderRadius: 6, padding: '10px 12px', color: '#ffffff', fontSize: 13,
                  resize: 'vertical', minHeight: 64, fontFamily: 'inherit'
                }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 260 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Select Decision Action:
              </div>
              {[
                { value: 'approve_for_underwriting', label: '✓ Approve for Credit Sanction', bg: decision === 'approve_for_underwriting' ? '#166534' : '#143322', border: '#22c55e' },
                { value: 'request_more_documents', label: '⊕ Request Additional KYC / Dossier', bg: decision === 'request_more_documents' ? '#854d0e' : '#2b2314', border: '#eab308' },
                { value: 'reject', label: '✗ Decline on Discrepancy / Alert FIU', bg: decision === 'reject' ? '#991b1b' : '#331515', border: '#ef4444' },
              ].map(({ value, label, bg, border }) => (
                <button
                  key={value}
                  onClick={() => setDecision(value)}
                  style={{
                    background: bg,
                    border: `1px solid ${border}`,
                    color: '#ffffff',
                    padding: '8px 12px',
                    borderRadius: 5,
                    fontSize: 12.5,
                    fontWeight: 600,
                    textAlign: 'left',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {label}
                </button>
              ))}

              <button
                className="btn btn-accent"
                onClick={submitReview}
                disabled={!decision || submitting}
                style={{ marginTop: 6, padding: '10px 14px', fontSize: 13 }}
              >
                {submitting ? 'Recording on Ledger...' : 'Commit Sign-Off Decision →'}
              </button>
            </div>
          </div>
        </div>
      )}

      {app.status === 'decided' && (
        <div className="card" style={{ marginTop: 24, borderLeft: '4px solid #6d28d9', background: '#f5f3ff' }}>
          <div style={{ color: '#5b21b6', fontWeight: 700, fontSize: 14 }}>
            ✓ Credit Decision Committed to Permanent Audit Ledger
          </div>
          <div style={{ color: '#4c1d95', fontSize: 13, marginTop: 4 }}>
            A certified credit underwriting officer has finalized and signed off on this credit dossier. All entries are hashed.
          </div>
        </div>
      )}
    </div>
  )
}
