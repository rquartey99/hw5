// The five agents as cards. The active one glows; each shows what it's doing and the last thing it said.
import { AGENT_INFO, type RunView } from '../runs'
import { AGENTS, type AgentName } from '../types'
import AgentAvatar from './AgentAvatar'
import type { DanMood } from './Dan'

const STATUS_LABEL = {
  idle: 'Standing by',
  thinking: 'Thinking',
  working: 'Working',
  waiting: 'Waiting',
  done: 'Done',
  error: 'Problem',
} as const

function bossMood(run: RunView | null): DanMood {
  if (!run) return 'sleepy'
  if (run.finished) return run.failed ? 'thinking' : 'wink'
  return run.agents.boss.status === 'idle' ? 'happy' : 'thinking'
}

export default function AgentFloor({ run }: { run: RunView | null }) {
  const card = (a: AgentName) => {
    const st = run?.agents[a]
    const involved = !!run && run.order.includes(a)
    const status = st?.status ?? 'idle'
    const active = !!run && !run.finished && run.active === a
    const activity = !run ? 'Standing by' : !involved && run.finished ? 'Not needed on this ticket' : st?.activity
    return (
      <article key={a} className={`agent-card status-${status}${active ? ' active' : ''}${a === 'boss' ? ' boss' : ''}`}>
        <div className="agent-head">
          <AgentAvatar agent={a} size={a === 'boss' ? 52 : 42} mood={bossMood(run)} />
          <div>
            <h3>{AGENT_INFO[a].label}</h3>
            <p className="agent-role">{AGENT_INFO[a].role}</p>
          </div>
        </div>
        <p className="agent-activity">
          <span className={`dot dot-${status}`} role="img" aria-label={STATUS_LABEL[status]} title={STATUS_LABEL[status]} />
          {activity}
        </p>
        {st?.said && <p className="agent-said"><span>“{st.said}”</span></p>}
      </article>
    )
  }
  return (
    <section className="floor" aria-label="Agent team">
      <div className="floor-boss">{card('boss')}</div>
      <div className="floor-team">{AGENTS.filter((a) => a !== 'boss').map(card)}</div>
    </section>
  )
}
