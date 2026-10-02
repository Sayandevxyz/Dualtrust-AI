import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, FileSearch, Plus, Shield, LogOut, Activity } from 'lucide-react'

export default function Layout() {
  const navigate = useNavigate()
  const logout = () => { localStorage.removeItem('token'); navigate('/login') }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">🛡</div>
          <div>
            <div className="logo-text">DualTrust AI</div>
            <div className="logo-sub">Verification Platform</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <LayoutDashboard size={16} /> Dashboard
          </NavLink>
          <NavLink to="/new" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Plus size={16} /> New Application
          </NavLink>
        </nav>

        <div style={{ padding: '0 12px 12px' }}>
          <div style={{ background: 'rgba(59,130,246,0.06)', borderRadius: 8, padding: 12, border: '1px solid rgba(59,130,246,0.15)', marginBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <Activity size={12} style={{ color: 'var(--accent-bright)' }} />
              <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--accent-bright)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>System Status</span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span>Groq (AI-A)</span><span style={{ color: 'var(--pass)' }}>● Online</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Mistral (AI-B)</span><span style={{ color: 'var(--pass)' }}>● Online</span>
              </div>
            </div>
          </div>

          <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 8, padding: 10, border: '1px solid var(--border)', marginBottom: 8 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--accent-bright)', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 4 }}>
              Team: Destroyers X
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              Rishabh · Ambrish · Praveen · Sayan · Neha
            </div>
          </div>
        </div>

        <div className="sidebar-user">
          <div className="user-avatar">DR</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Demo Reviewer</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>reviewer</div>
          </div>
          <button onClick={logout} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4 }}>
            <LogOut size={14} />
          </button>
        </div>
      </aside>

      <main className="main-content fade-in">
        <Outlet />
      </main>
    </div>
  )
}
