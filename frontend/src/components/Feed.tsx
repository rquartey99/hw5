// The full back-and-forth for a run, newest at the bottom. Open while the team works, folded after.
import { useEffect, useRef } from 'react'
import { AGENT_INFO, type RunView } from '../runs'
import { clock } from '../format'
import AgentAvatar from './AgentAvatar'

export default function Feed({ run }: { run: RunView }) {
  const list = useRef<HTMLOListElement>(null)
  // Follow new steps inside the feed box only; never scroll the page itself.
  useEffect(() => {
    const el = list.current
    if (el && !run.finished) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [run.feed.length, run.finished])

  return (
    <details className="feed" open={!run.finished} key={`${run.runId}-${run.finished}`}>
      <summary>
        Conversation <span className="feed-count">{run.feed.length} steps</span>
      </summary>
      <ol className="feed-list" ref={list}>
        {run.feed.map((f) => (
          <li key={f.key} className={`feed-item kind-${f.kind}`}>
            <span className="feed-who">
              {f.who === 'human' || f.who === 'system' ? (
                <span className={`avatar avatar-${f.who}`} style={{ width: 24, height: 24 }} aria-hidden="true">
                  {f.who === 'human' ? '✍' : '•'}
                </span>
              ) : (
                <AgentAvatar agent={f.who} size={24} />
              )}
              <b>{f.who === 'human' ? 'You' : f.who === 'system' ? 'Desk' : AGENT_INFO[f.who].label}</b>
            </span>
            <span className="feed-text">{f.text}</span>
            <time className="feed-time">{clock(f.time)}</time>
          </li>
        ))}
      </ol>
    </details>
  )
}
