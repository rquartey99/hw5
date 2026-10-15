// After (or during) a run: one short card per agent that finished its part.
import { AGENT_INFO, type RunView } from '../runs'
import AgentAvatar from './AgentAvatar'

const STATUS_TEXT = { done: 'Done', needs_human: 'Needs a person', blocked: 'Blocked', info: 'FYI' } as const

export default function Summaries({ run }: { run: RunView }) {
  const finished = run.order.filter((a) => run.agents[a].report)
  if (!finished.length) return null
  // Boss first: it has the final word.
  const ordered = [...finished].sort((a, b) => (a === 'boss' ? -1 : b === 'boss' ? 1 : 0))
  return (
    <section className="summaries" aria-label="What each agent did">
      <h2 className="section-title">What each agent did</h2>
      <div className="summary-grid">
        {ordered.map((a) => {
          const r = run.agents[a].report!
          return (
            <article key={a} className={`summary-card${a === 'boss' ? ' summary-boss' : ''}`}>
              <header>
                <AgentAvatar agent={a} size={30} mood="wink" />
                <strong>{a === 'boss' ? 'Boss · final word' : AGENT_INFO[a].label}</strong>
                <span className={`pill pill-${r.status}`}>{STATUS_TEXT[r.status] ?? r.status}</span>
              </header>
              <p>{r.summary}</p>
              {r.actions_taken.length > 0 && (
                <ul className="summary-list">
                  {r.actions_taken.map((x, i) => <li key={i}>{x}</li>)}
                </ul>
              )}
              {r.needs_human.length > 0 && (
                <ul className="summary-list needs">
                  {r.needs_human.map((x, i) => <li key={i}>{x}</li>)}
                </ul>
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}
