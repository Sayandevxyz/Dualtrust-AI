import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { applications, documents } from '../api/client'
import { Upload, Plus } from 'lucide-react'

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
    <div className="fade-in" style={{ maxWidth: 600 }}>
      <div className="page-header">
        <h1 className="page-title">New Application</h1>
        <p className="page-subtitle">Upload documents for dual-pipeline AI verification</p>
      </div>

      {step === 1 && (
        <div className="card">
          <div style={{ display: 'grid', gap: 16 }}>
            {[
              { label: 'Applicant Name', key: 'applicant_name', type: 'text', placeholder: 'Full legal name' },
              { label: 'Loan Amount (₹)', key: 'loan_amount', type: 'number', placeholder: '1500000' },
            ].map(({ label, key, type, placeholder }) => (
              <div key={key}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>{label}</label>
                <input
                  type={type}
                  placeholder={placeholder}
                  value={(form as any)[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  style={{
                    width: '100%', background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                    borderRadius: 8, padding: '10px 14px', color: 'var(--text-primary)', fontSize: 14,
                    fontFamily: 'inherit', outline: 'none',
                  }}
                />
              </div>
            ))}
            <div>
              <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>Loan Type</label>
              <select
                value={form.loan_type}
                onChange={e => setForm(f => ({ ...f, loan_type: e.target.value }))}
                style={{
                  width: '100%', background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                  borderRadius: 8, padding: '10px 14px', color: 'var(--text-primary)', fontSize: 14, fontFamily: 'inherit',
                }}
              >
                {['personal', 'home', 'business', 'vehicle', 'education'].map(t => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
            </div>
            <button
              className="btn btn-primary"
              onClick={createApp}
              disabled={!form.applicant_name || !form.loan_amount}
            >
              <Plus size={14} /> Create Application
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="card">
          <div style={{ fontWeight: 700, marginBottom: 16 }}>Upload Documents</div>
          <div
            className="upload-zone"
            onDrop={e => { e.preventDefault(); setFiles(f => [...f, ...Array.from(e.dataTransfer.files)]) }}
            onDragOver={e => e.preventDefault()}
            onClick={() => document.getElementById('file-input')?.click()}
          >
            <Upload size={32} style={{ color: 'var(--accent)', marginBottom: 12 }} />
            <div style={{ fontWeight: 600, marginBottom: 4 }}>Drop documents here or click to browse</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>PDF, PNG, JPG supported · Salary slips, bank statements, ITR, PAN, Aadhaar</div>
            <input id="file-input" type="file" multiple accept=".pdf,.png,.jpg,.jpeg" style={{ display: 'none' }}
              onChange={e => setFiles(f => [...f, ...Array.from(e.target.files || [])])} />
          </div>

          {files.length > 0 && (
            <div style={{ marginTop: 16 }}>
              {files.map((f, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
                  <span>{f.name}</span>
                  <span style={{ color: 'var(--text-muted)' }}>{(f.size / 1024).toFixed(0)} KB</span>
                </div>
              ))}
            </div>
          )}

          <button className="btn btn-primary" onClick={uploadAndAnalyze} disabled={files.length === 0 || uploading} style={{ marginTop: 20, width: '100%', justifyContent: 'center' }}>
            {uploading ? 'Uploading & Analyzing...' : `Upload ${files.length} Document(s) & Start Analysis →`}
          </button>
        </div>
      )}
    </div>
  )
}
