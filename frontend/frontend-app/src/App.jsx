import { useState, useEffect, useCallback } from 'react'

const API = 'http://localhost:8000'

function App() {
  const [tab, setTab] = useState('projects')
  const [projects, setProjects] = useState([])
  const [tasks, setTasks] = useState([])
  const [weeklyPlans, setWeeklyPlans] = useState([])
  const [availability, setAvailability] = useState([])
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState({})
  const [toast, setToast] = useState(null)

  const showToast = (title, message, type = 'info') => {
    setToast({ title, message, type })
    setTimeout(() => setToast(null), 5000)
  }

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, projectsRes, tasksRes, plansRes, availRes] = await Promise.allSettled([
        fetch(`${API}/api/status`).then(r => r.json()),
        fetch(`${API}/api/projects`).then(r => r.json()),
        fetch(`${API}/api/tasks`).then(r => r.json()),
        fetch(`${API}/api/weekly-plans`).then(r => r.json()),
        fetch(`${API}/api/availability`).then(r => r.json()),
      ])
      if (statusRes.status === 'fulfilled') setStatus(statusRes.value)
      if (projectsRes.status === 'fulfilled') setProjects(projectsRes.value.projects || [])
      if (tasksRes.status === 'fulfilled') setTasks(tasksRes.value.tasks || [])
      if (plansRes.status === 'fulfilled') setWeeklyPlans(plansRes.value.weekly_plans || [])
      if (availRes.status === 'fulfilled') setAvailability(availRes.value.availability || [])
    } catch (e) {
      console.error('Fetch error', e)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const handleSync = async () => {
    setLoading(l => ({ ...l, sync: true }))
    showToast('Syncing…', 'Fetching issues & PRs from GitHub', 'info')
    try {
      const res = await fetch(`${API}/api/sync`, { method: 'POST' })
      const data = await res.json()
      if (res.ok) {
        showToast('Sync Complete ✅', data.message, 'success')
        fetchData()
      } else {
        showToast('Sync Failed', data.detail || 'Unknown error', 'error')
      }
    } catch (e) {
      showToast('Sync Error', e.message, 'error')
    }
    setLoading(l => ({ ...l, sync: false }))
  }

  const handlePlan = async () => {
    setLoading(l => ({ ...l, plan: true }))
    showToast('Planning…', 'Generating your weekly plan with AI', 'info')
    try {
      const res = await fetch(`${API}/api/plan`, { method: 'POST' })
      const data = await res.json()
      if (res.ok) {
        showToast('Plan Ready 📅', data.message, 'success')
        setTab('plan')
        fetchData()
      } else {
        showToast('Plan Failed', data.detail || 'Unknown error', 'error')
      }
    } catch (e) {
      showToast('Plan Error', e.message, 'error')
    }
    setLoading(l => ({ ...l, plan: false }))
  }

  const handleSetup = async () => {
    setLoading(l => ({ ...l, setup: true }))
    showToast('Setting Up…', 'Creating Notion databases & seeding data', 'info')
    try {
      const res = await fetch(`${API}/api/setup`, { method: 'POST' })
      const data = await res.json()
      if (res.ok) {
        showToast('Setup Complete 🎉', data.message, 'success')
        fetchData()
      } else {
        showToast('Setup Failed', data.detail || 'Unknown error', 'error')
      }
    } catch (e) {
      showToast('Setup Error', e.message, 'error')
    }
    setLoading(l => ({ ...l, setup: false }))
  }

  const openTasks = tasks.filter(t => t.Status === 'Open' || t.Status === 'In Progress')
  const mergedTasks = tasks.filter(t => t.Status === 'Merged')
  const totalHours = availability.reduce((sum, a) => sum + (parseFloat(a['Available Hours']) || 0), 0)

  return (
    <>
      <div className="ambient-bg" />

      {/* ─── Header ─── */}
      <header className="header">
        <div className="header-logo">
          <span className="logo-icon">🚀</span>
          <h1>GSoC Command Center</h1>
        </div>
        <div className="header-badge">
          <span className="dot" />
          {status?.configured?.notion ? 'Notion Connected' : 'Disconnected'}
        </div>
        <div className="header-actions">
          {!status?.configured?.projects_db && (
            <button className="btn btn-ghost" onClick={handleSetup} disabled={loading.setup}>
              {loading.setup ? <span className="spinner" /> : '⚡'} Setup
            </button>
          )}
          <button className="btn btn-primary" onClick={handleSync} disabled={loading.sync}>
            {loading.sync ? <span className="spinner" /> : '🔄'} Sync from GitHub
          </button>
          <button className="btn btn-success" onClick={handlePlan} disabled={loading.plan}>
            {loading.plan ? <span className="spinner" /> : '🧠'} Plan my Week
          </button>
        </div>
      </header>

      {/* ─── Main ─── */}
      <main className="main">
        {/* Stats */}
        <div className="stats-row">
          <StatCard icon="📁" label="Projects" value={projects.length} sub="GSoC organizations" />
          <StatCard icon="🔥" label="Open Tasks" value={openTasks.length} sub="Issues & PRs to work on" />
          <StatCard icon="✅" label="Merged" value={mergedTasks.length} sub="Contributions merged" />
          <StatCard icon="⏰" label="Available Hours" value={totalHours} sub="This week" />
        </div>

        {/* Tabs */}
        <div className="tabs">
          {[
            { key: 'projects', label: '📁 Projects', count: projects.length },
            { key: 'tasks', label: '✅ Tasks', count: tasks.length },
            { key: 'plan', label: '📅 Weekly Plan', count: weeklyPlans.length },
            { key: 'availability', label: '⏰ Availability', count: availability.length },
          ].map(t => (
            <button
              key={t.key}
              className={`tab ${tab === t.key ? 'active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              {t.label} ({t.count})
            </button>
          ))}
        </div>

        {/* Content */}
        {tab === 'projects' && <ProjectsView projects={projects} />}
        {tab === 'tasks' && <TasksView tasks={tasks} />}
        {tab === 'plan' && <PlanView plans={weeklyPlans} />}
        {tab === 'availability' && <AvailabilityView availability={availability} />}
      </main>

      {/* ─── Footer ─── */}
      <footer className="footer">
        © 2026 GSOC COMMAND CENTER • Built with Notion MCP + React + FastAPI
      </footer>

      {/* Toast */}
      {toast && (
        <div className={`toast ${toast.type}`}>
          <div className="toast-title">{toast.title}</div>
          <div className="toast-message">{toast.message}</div>
        </div>
      )}
    </>
  )
}

/* ─── Stat Card ──────────────────────────────── */
function StatCard({ icon, label, value, sub }) {
  return (
    <div className="stat-card">
      <div className="stat-icon">{icon}</div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-sub">{sub}</div>
    </div>
  )
}

/* ─── Projects View ──────────────────────────── */
function ProjectsView({ projects }) {
  if (!projects.length) return <EmptyState icon="📁" msg="No projects yet. Run Setup to create and seed your Notion databases." />
  return (
    <div className="projects-grid">
      {projects.map(p => (
        <div key={p.id} className={`project-card priority-${p.Priority}`}>
          <div className="project-name">{p.Project}</div>
          <div className="project-org">{p.Org}</div>
          <div className="project-meta">
            <span className="badge badge-status" data-status={p.Status}>{p.Status}</span>
            <span className="badge badge-priority" data-priority={p.Priority}>{p.Priority}</span>
            <span className="badge badge-difficulty" data-difficulty={p.Difficulty}>{p.Difficulty}</span>
            {p.Tags && p.Tags.split(', ').map(tag => (
              <span key={tag} className="badge badge-tag">{tag}</span>
            ))}
          </div>
          {p.Repo && (
            <a href={p.Repo} target="_blank" rel="noreferrer" className="project-link">
              View Repository →
            </a>
          )}
        </div>
      ))}
    </div>
  )
}

/* ─── Tasks View ──────────────────────────────── */
function TasksView({ tasks }) {
  if (!tasks.length) return <EmptyState icon="✅" msg="No tasks synced yet. Click 'Sync from GitHub' to pull issues & PRs into Notion." />
  return (
    <div className="card">
      <div className="card-header">
        <h2>✅ GitHub Issues & Pull Requests</h2>
        <span className="badge badge-tag">{tasks.length} total</span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table className="tasks-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Repo</th>
              <th>Type</th>
              <th>Status</th>
              <th>Assignee</th>
              <th>Labels</th>
              <th>Link</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map(t => (
              <tr key={t.id}>
                <td title={t.Title}>{t.Title}</td>
                <td>{t.Repo}</td>
                <td><span className="badge badge-type" data-type={t.Type}>{t.Type}</span></td>
                <td><span className="badge badge-status" data-status={t.Status}>{t.Status}</span></td>
                <td>{t.Assignee || '—'}</td>
                <td>{t.Labels || '—'}</td>
                <td>
                  {t.URL && <a href={t.URL} target="_blank" rel="noreferrer">View →</a>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ─── Plan View ──────────────────────────────── */
function PlanView({ plans }) {
  if (!plans.length) return <EmptyState icon="📅" msg="No weekly plans yet. Click 'Plan my Week' to generate an AI-powered schedule!" />
  const latest = plans[0]
  return (
    <div className="card">
      <div className="card-header">
        <h2>📅 {latest.Week || 'Weekly Plan'}</h2>
        <span className="badge badge-tag">{latest['Available Hours'] || 0}h available</span>
      </div>
      <div className="card-body">
        {latest['AI Summary'] && (
          <div className="plan-summary">{latest['AI Summary']}</div>
        )}
      </div>
    </div>
  )
}

/* ─── Availability View ──────────────────────── */
function AvailabilityView({ availability }) {
  if (!availability.length) return <EmptyState icon="⏰" msg="No availability data. Run Setup to seed sample data." />
  return (
    <div className="plan-days">
      {availability.map(a => (
        <div key={a.id} className="plan-day">
          <div className="day-header">
            <span className="day-name">{a.Date}</span>
            <span className="day-hours">{a['Available Hours']}h</span>
          </div>
          {a.Notes && <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>{a.Notes}</div>}
        </div>
      ))}
    </div>
  )
}

/* ─── Empty State ──────────────────────────────── */
function EmptyState({ icon, msg }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <p>{msg}</p>
    </div>
  )
}

export default App
