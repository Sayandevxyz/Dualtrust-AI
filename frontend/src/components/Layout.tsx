import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { FolderKanban, FilePlus2, ShieldCheck, LogOut, CheckCircle2, ShieldAlert } from 'lucide-react'
import { LogoIcon } from './Logo'

export default function Layout() {
  const navigate = useNavigate()
  const logout = () => { localStorage.removeItem('token'); navigate('/login') }

  return (
    <div>
      {/* Institutional Top Compliance Bar */}
      <div className="bank-system-banner">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            background: '#ffffff',
            borderRadius: 4,
            padding: '2px 4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <LogoIcon size={14} />
          </div>
          <span style={{ fontWeight: 800, color: '#f8fafc', letterSpacing: '0.08em' }}>
            DUALTRUST <span style={{ color: '#f79f1a' }}>AI</span>
          </span>
          <span style={{ color: '#475569' }}>|</span>
          <span>COMMERCIAL CREDIT &amp; RISK UNDERWRITING SYSTEM</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <span style={{ color: '#94a3b8' }}>WORKSTATION ID: <span className="mono" style={{ color: '#cbd5e1' }}>MUM-UW-4029</span></span>
          <span className="badge-compliance">ISO 27001 SECURE</span>
        </div>
      </div>

      <div className="layout">
        <aside className="sidebar">
          {/* DualTrust AI Brand Header */}
          <div className="sidebar-header" style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
            <div style={{
              width: 42,
              height: 42,
              background: '#ffffff',
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.25)',
              padding: 4,
              flexShrink: 0,
            }}>
              <LogoIcon size={30} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, lineHeight: 1.1 }}>
                <span style={{ fontSize: 16, fontWeight: 800, color: '#ffffff', letterSpacing: '-0.2px' }}>DUALTRUST</span>
                <span style={{ fontSize: 16, fontWeight: 800, color: '#f79f1a', letterSpacing: '-0.2px' }}>AI</span>
              </div>
              <div className="sidebar-bank-subtitle" style={{ marginTop: 3 }}>Credit Risk Assessment</div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="sidebar-nav">
            <div className="sidebar-nav-heading">Underwriting Station</div>
            <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <FolderKanban size={16} /> Underwriting Queue
            </NavLink>
            <NavLink to="/new" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <FilePlus2 size={16} /> New Credit Dossier
            </NavLink>
          </nav>

          {/* System & Engine Telemetry */}
          <div className="sidebar-telemetry">
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <ShieldCheck size={13} style={{ color: '#60a5fa' }} />
              <span style={{ fontSize: 10, fontWeight: 700, color: '#93c5fd', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Dual-AI Verification Engine
              </span>
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Groq Llama-3 (Pipeline A)</span>
                <span style={{ color: '#4ade80', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 3 }}>
                  <CheckCircle2 size={10} /> Active
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Mistral Large (Pipeline B)</span>
                <span style={{ color: '#4ade80', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 3 }}>
                  <CheckCircle2 size={10} /> Active
                </span>
              </div>
              <div style={{ borderTop: '1px solid #1a2a40', marginTop: 4, paddingTop: 4, display: 'flex', justifyContent: 'space-between' }}>
                <span>Hash Audit Chain</span>
                <span style={{ color: '#cbd5e1', fontWeight: 600 }}>SHA-256 Valid</span>
              </div>
            </div>
          </div>

          {/* Institutional User Profile */}
          <div className="sidebar-user">
            <div className="user-avatar">DR</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#ffffff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                Demo Underwriter
              </div>
              <div style={{ fontSize: 11, color: '#94a3b8' }}>Sr. Credit Officer</div>
            </div>
            <button onClick={logout} title="Sign Out of Terminal" style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', padding: 4 }}>
              <LogOut size={15} />
            </button>
          </div>
        </aside>

        <main className="main-content fade-in">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
