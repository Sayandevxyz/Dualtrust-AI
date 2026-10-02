import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { applications, documents } from '../api/client'
import { Upload, Plus, FileText, ArrowRight, ShieldCheck, CheckCircle2 } from 'lucide-react'

export default function NewApplication() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ applicant_name: '', loan_type: 'personal', loan_amount: '' })
  const [appId, setAppId] = useState<string | null>(null)
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [step, setStep] = useState(1)

  const createApp = async () => {
    const r = await applications.create({
      applicant_name: form.applicant_name,
      loan_type: form.loan_type,
      loan_amount: parseFloat(form.loan_amount),
    })
    setAppId(r.data.id)
    setStep(2)
  }

  const uploadAndAnalyze = async () => {
    if (!appId) return
    setUploading(true)
    for (const file of files) {
      const docR = await documents.upload(appId, file)
      await documents.analyze(docR.data.id)
    }
    setUploading(false)
    navigate(`/applications/${appId}`)
  }

  return (
    <div className="fade-in" style={{ maxWidth: 680, margin: '0 auto' }}>
      {/* Page Title */}
      <div className="page-header" style={{ marginBottom: 20 }}>
        <h1 className="page-title">Initiate Loan Dossier Verification</h1>
        <p className="page-subtitle">
          Intake borrower financial documents for dual-AI independent audit and policy rule execution
        </p>
      </div>

      {/* Step Indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          color: step === 1 ? 'var(--bank-navy)' : 'var(--risk-pass-bar)',
          fontWeight: 600, fontSize: 13
        }}>
          <span style={{
            width: 24, height: 24, borderRadius: '50%',
            background: step === 1 ? 'var(--bank-navy)' : 'var(--risk-pass-bar)',
            color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 12, fontWeight: 700
          }}>1</span>
          Borrower &amp; Facility Details
        </div>
        <div style={{ flex: 1, height: 2, background: step === 2 ? 'var(--bank-navy)' : 'var(--bank-border)' }} />
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          color: step === 2 ? 'var(--bank-navy)' : 'var(--bank-text-muted)',
          fontWeight: 600, fontSize: 13
        }}>
          <span style={{
            width: 24, height: 24, borderRadius: '50%',
            background: step === 2 ? 'var(--bank-navy)' : 'var(--bank-border)',
            color: step === 2 ? '#ffffff' : 'var(--bank-text-muted)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 12, fontWeight: 700
          }}>2</span>
          KYC &amp; Income Dossier Upload
        </div>
      </div>

      {/* Stage 1: Borrower Information */}
      {step === 1 && (
        <div className="card" style={{ borderTop: '4px solid var(--bank-navy)' }}>
          <div className="card-header">
            <span className="card-title">Credit Facility Application Details</span>
            <span style={{ fontSize: 12, color: 'var(--bank-text-muted)' }}>Mandatory KYC Fields</span>
          </div>

          <div style={{ display: 'grid', gap: 18 }}>
            <div>
              <label style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--bank-text-secondary)', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Primary Applicant Full Legal Name
              </label>
              <input
                type="text"
                placeholder="e.g. Priya Sharma"
                value={form.applicant_name}
                onChange={e => setForm(f => ({ ...f, applicant_name: e.target.value }))}
                style={{ width: '100%', fontSize: 14 }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div>
                <label style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--bank-text-secondary)', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Facility Category
                </label>
                <select
                  value={form.loan_type}
                  onChange={e => setForm(f => ({ ...f, loan_type: e.target.value }))}
                  style={{ width: '100%', fontSize: 13.5 }}
                >
                  <option value="personal">Personal Loan Facility</option>
                  <option value="home">Home / Mortgage Facility</option>
                  <option value="business">Commercial Business Loan</option>
                  <option value="vehicle">Auto / Vehicle Finance</option>
                  <option value="education">Education Loan</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--bank-text-secondary)', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Sanction Request Amount (₹)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 1500000"
                  value={form.loan_amount}
                  onChange={e => setForm(f => ({ ...f, loan_amount: e.target.value }))}
                  style={{ width: '100%', fontSize: 14 }}
                />
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--bank-border)', paddingTop: 18, display: 'flex', justifyContent: 'flex-end' }}>
              <button
                className="btn btn-primary"
                onClick={createApp}
                disabled={!form.applicant_name || !form.loan_amount}
                style={{ padding: '10px 20px', fontSize: 13.5 }}
              >
                Proceed to Document Intake <ArrowRight size={15} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stage 2: Document Intake */}
      {step === 2 && (
        <div className="card" style={{ borderTop: '4px solid var(--bank-blue)' }}>
          <div className="card-header">
            <div>
              <span className="card-title">Income, Tax &amp; Identity Dossier</span>
              <div style={{ fontSize: 12, color: 'var(--bank-text-muted)', marginTop: 2 }}>
                Upload official bank statements, salary slips, Form 16 / ITR, PAN or Aadhaar
              </div>
            </div>
            <span className="mono" style={{ fontSize: 11, color: 'var(--bank-navy)', fontWeight: 600 }}>
              APP: {appId?.slice(0, 10)}
            </span>
          </div>

          <div
            className="upload-zone"
            onDrop={e => { e.preventDefault(); setFiles(f => [...f, ...Array.from(e.dataTransfer.files)]) }}
            onDragOver={e => e.preventDefault()}
            onClick={() => document.getElementById('file-input')?.click()}
          >
            <Upload size={32} style={{ color: 'var(--bank-blue)', margin: '0 auto 10px', display: 'block' }} />
            <div style={{ fontWeight: 600, color: 'var(--bank-navy)', fontSize: 14 }}>
              Click to browse or drop documents into secure intake zone
            </div>
            <div style={{ fontSize: 12, color: 'var(--bank-text-muted)', marginTop: 4 }}>
              Accepts PDF, PNG, JPG files. Documents are processed under dual-pipeline cryptographic validation.
            </div>
            <input
              id="file-input"
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg"
              style={{ display: 'none' }}
              onChange={e => setFiles(f => [...f, ...Array.from(e.target.files || [])])}
            />
          </div>

          {files.length > 0 && (
            <div style={{ marginTop: 18 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--bank-text-secondary)', textTransform: 'uppercase', marginBottom: 8 }}>
                Queued Instruments ({files.length}):
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {files.map((f, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: 'var(--bank-surface-muted)', border: '1px solid var(--bank-border)', borderRadius: 5, fontSize: 13 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <FileText size={15} color="var(--bank-navy)" />
                      <span style={{ fontWeight: 500, color: 'var(--bank-navy)' }}>{f.name}</span>
                    </div>
                    <span className="mono" style={{ color: 'var(--bank-text-muted)', fontSize: 12 }}>
                      {(f.size / 1024).toFixed(0)} KB
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ borderTop: '1px solid var(--bank-border)', marginTop: 20, paddingTop: 16 }}>
            <button
              className="btn btn-primary"
              onClick={uploadAndAnalyze}
              disabled={files.length === 0 || uploading}
              style={{ width: '100%', padding: '11px', fontSize: 13.5, justifyContent: 'center' }}
            >
              {uploading ? (
                <>
                  <div className="spinner" style={{ borderTopColor: '#ffffff', marginRight: 6 }} />
                  Processing Dual-Pipeline AI Verification...
                </>
              ) : (
                `Initiate Automated Verification (${files.length} documents) →`
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
