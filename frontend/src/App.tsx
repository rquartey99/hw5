import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, API_BASE } from './api'
import AgentFloor from './components/AgentFloor'
import ApprovalCard from './components/ApprovalCard'
import Dan from './components/Dan'
import ElmLeaf from './components/ElmLeaf'
import Feed from './components/Feed'
import Summaries from './components/Summaries'
import TicketList from './components/TicketList'
import { money } from './format'
import { AGENT_INFO, runsSinceReset } from './runs'
import { formatDeskDate, seasonFor } from './season'
import type { Approval, AuditEvent, Cash, Ticket } from './types'

const FAST_POLL_MS = 1200 // while the team is working
const SLOW_POLL_MS = 4000 // otherwise
const LOW_BALANCE = 500 // accounting's rule: warn below $500

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [approvals, setApprovals] = useState<Approval[]>([])
  // The selected ticket lives in the URL (#102) so a refresh keeps your place.
  const [selectedId, setSelectedId] = useState<number | null>(() => Number(location.hash.slice(1)) || null)
  const [online, setOnline] = useState<boolean | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [busyApproval, setBusyApproval] = useState<string | null>(null)
  const [approver, setApprover] = useState(() => localStorage.getItem('cc-approver') ?? '')
  const next = useRef<number | null>(null)

  const runs = useMemo(() => runsSinceReset(events), [events])
  const activeRun = runs.find((r) => !r.finished) ?? null
  const selected = tickets.find((t) => t.id === selectedId) ?? null
  const runForSelected = [...runs].reverse().find((r) => r.ticketId === selectedId) ?? null
  const pending = approvals.filter((a) => a.status === 'pending')
  const season = seasonFor(cash?.date)

  const refresh = useCallback(async () => {
    try {
      const [ev, t, c, ap] = await Promise.all([api.events(next.current), api.tickets(), api.cash(), api.approvals()])
      if (ev.events.length) {
        setEvents((prev) => {
          const last = prev.length ? prev[prev.length - 1].index : -1
          return [...prev, ...ev.events.filter((e) => e.index > last)]
        })
      }
      next.current = ev.next
      setTickets(t)
      setCash(c)
      setApprovals(ap)
      setOnline(true)
    } catch {
      setOnline(false)
    }
  }, [])

  // Poll fast while a run is going, slowly otherwise.
  useEffect(() => {
    let alive = true
    let timer: number
    const tick = async () => {
      await refresh()
      if (alive) timer = window.setTimeout(tick, activeRun ? FAST_POLL_MS : SLOW_POLL_MS)
    }
    tick()
    return () => {
      alive = false
      window.clearTimeout(timer)
    }
  }, [refresh, activeRun])

  // Default selection: the ticket being worked on, else the first open one.
  useEffect(() => {
    if (selectedId !== null || !tickets.length) return
    setSelectedId(activeRun?.ticketId ?? tickets.find((t) => t.state === 'open')?.id ?? tickets[0].id)
  }, [tickets, selectedId, activeRun])

  useEffect(() => localStorage.setItem('cc-approver', approver), [approver])
  useEffect(() => {
    if (selectedId !== null) history.replaceState(null, '', `#${selectedId}`)
  }, [selectedId])

  useEffect(() => {
    if (!toast) return
    const t = window.setTimeout(() => setToast(null), 5000)
    return () => window.clearTimeout(t)
  }, [toast])

  const start = async () => {
    if (!selected) return
    setStarting(true)
    try {
      await api.run(selected.id)
      await refresh()
    } catch (e) {
      setToast((e as Error).message)
    } finally {
      setStarting(false)
    }
  }

  const decide = async (item: Approval, ok: boolean) => {
    setBusyApproval(item.id)
    try {
      const res = ok ? await api.approve(item.id, approver.trim()) : await api.reject(item.id, approver.trim())
      if (res.status === 'failed') setToast(`Payment didn't go through: ${JSON.stringify(res.result)}`)
      await refresh()
    } catch (e) {
      setToast((e as Error).message)
    } finally {
      setBusyApproval(null)
    }
  }

  const reset = async () => {
    if (!window.confirm('Reset the shop database to its original values? The audit trail is kept.')) return
    try {
      await api.reset()
      await refresh()
      setToast('Fresh start: the database is back to its original values.')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  const low = cash !== null && cash.balance < LOW_BALANCE
  const selectedRunning = activeRun?.ticketId === selectedId

  return (
    <div className={`app season-${season.key}`}>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <Dan size={40} mood={activeRun ? 'thinking' : 'happy'} badge />
            <div>
              <h1>Campus Customs <span>Desk</span></h1>
              <p className="brand-sub">The agent team, at work on today’s tickets</p>
            </div>
          </div>
          <div className="season-chip" title={season.greeting}>
            <ElmLeaf size={18} />
            <span>
              <b>{formatDeskDate(cash?.date)}</b> · {season.label}
            </span>
          </div>
          <div className="topbar-right">
            <label className="approver">
              <span>Approving as</span>
              <input value={approver} onChange={(e) => setApprover(e.target.value)} placeholder="your name" />
            </label>
            <div className={`balance${low ? ' low' : ''}`} key={cash?.balance}>
              <span className="balance-label">Checking</span>
              <span className="balance-amount">{cash ? money(cash.balance) : '—'}</span>
              {low && <span className="balance-warn">Below $500</span>}
            </div>
          </div>
        </div>
        <div className="leaves" aria-hidden="true">
          {[0, 1, 2, 3, 4].map((i) => <ElmLeaf key={i} size={14 + (i % 3) * 4} className={`leaf leaf-${i}`} />)}
        </div>
      </header>

      {online === false && (
        <div className="offline">
          Can’t reach the backend at <code>{API_BASE}</code>. Start it from <code>backend/</code> with{' '}
          <code>uvicorn main:app --reload --port 8000</code>.
        </div>
      )}

      <main className="layout">
        <TicketList tickets={tickets} selectedId={selectedId} runningTicketId={activeRun?.ticketId ?? null}
          onSelect={setSelectedId} />

        <div className="stage">
          {pending.length > 0 && (
            <section className="approvals" aria-label="Waiting for your approval">
              {pending.map((p) => (
                <ApprovalCard key={p.id} item={p} approver={approver.trim()} busy={busyApproval === p.id}
                  onApprove={() => decide(p, true)} onReject={() => decide(p, false)} />
              ))}
            </section>
          )}

          {selected && (
            <section className="run-head">
              <div>
                <p className="eyebrow">Ticket #{selected.id} · {selected.requester}</p>
                <h2>{selected.subject}</h2>
                {selected.notes && <p className="run-notes">{selected.notes.split('\n')[0]}</p>}
              </div>
              <div className="run-actions">
                {selectedRunning ? (
                  <span className="working"><span className="spinner" /> Team is on it…</span>
                ) : (
                  <button className="btn btn-primary btn-lg" onClick={start}
                    disabled={starting || !!activeRun || selected.state === 'resolved' || online === false}
                    title={activeRun ? `The team is busy with ticket #${activeRun.ticketId}` : undefined}>
                    {starting ? 'Starting…' : selected.state === 'resolved' ? 'Resolved' : 'Send in the team'}
                  </button>
                )}
              </div>
            </section>
          )}

          {runForSelected && runForSelected.chain.length > 0 && (
            <nav className="chain" aria-label="Who handed work to whom">
              {runForSelected.chain.map((a, i) => (
                <span key={a + i}>{i > 0 && <span className="chain-arrow">→</span>}<span className="chain-step">{AGENT_INFO[a].label}</span></span>
              ))}
            </nav>
          )}

          <AgentFloor run={runForSelected} />

          {!runForSelected && selected && (
            <p className="empty">
              No run on this ticket yet. Press <b>Send in the team</b> and the boss will take it from there.
            </p>
          )}

          {runForSelected && <Summaries run={runForSelected} />}
          {runForSelected && <Feed run={runForSelected} />}
        </div>
      </main>

      <footer className="foot">
        <span className={`conn ${online ? 'ok' : online === false ? 'down' : ''}`}>
          {online ? 'Connected' : online === false ? 'Offline' : 'Connecting'} · {API_BASE}
        </span>
        <span className="foot-greeting">{season.greeting}</span>
        <button className="btn btn-link" onClick={reset} disabled={!!activeRun}>Reset shop data</button>
      </footer>

      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  )
}
