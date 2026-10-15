// Turns the raw audit trail into what the board shows: runs per ticket, each agent's live state, and a feed.
import { AGENTS, type AgentName, type AuditEvent, type AuditPart, type TaskReport } from './types'

export type AgentStatus = 'idle' | 'thinking' | 'working' | 'waiting' | 'done' | 'error'

export interface AgentState {
  status: AgentStatus
  activity: string // one line: what it's doing right now
  said: string | null // last thing it said in words
  report: TaskReport | null
}

export type FeedKind = 'task' | 'tool' | 'result' | 'say' | 'delegate' | 'done' | 'human' | 'system' | 'error' | 'pending'

export interface FeedItem {
  key: string
  who: AgentName | 'human' | 'system'
  kind: FeedKind
  text: string
  time: string
}

export interface RunView {
  runId: string
  ticketId: number | null
  startIndex: number
  finished: boolean
  failed: boolean
  resolved: boolean
  agents: Record<AgentName, AgentState>
  chain: AgentName[] // deepest hand-off path seen in the run, e.g. boss -> facilities -> accounting
  active: AgentName | null
  feed: FeedItem[]
  order: AgentName[] // agents in the order they joined the run
}

export const AGENT_INFO: Record<AgentName, { label: string; role: string }> = {
  boss: { label: 'Boss', role: 'Routes tickets, makes the call' },
  inventory: { label: 'Inventory', role: 'Stock, shipping, restocks' },
  accounting: { label: 'Accounting', role: 'Cash, prices, payments' },
  facilities: { label: 'Facilities', role: 'Lease and rent' },
  customer_service: { label: 'Customer Service', role: 'Talks to requesters' },
}

const TOOL_PHRASES: Record<string, string> = {
  list_open_tickets: 'Scanning the open tickets',
  get_ticket: 'Reading the ticket',
  update_ticket: 'Updating the ticket',
  check_order_fulfillment: 'Checking if the order can ship',
  check_stock: 'Checking the shelves',
  fulfill_order: 'Shipping from stock',
  list_vendors: 'Looking up vendors',
  quote_bulk_discount: 'Pricing a discount',
  get_cash_position: 'Checking the cash',
  get_lease: 'Pulling up the lease',
  record_payment: 'Requesting a payment',
  add_desk_note: 'Leaving a desk note',
}

const isAgent = (who: string): who is AgentName => (AGENTS as string[]).includes(who)
export const toolPhrase = (tool: string) => TOOL_PHRASES[tool] ?? `Using ${tool}`

function short(value: unknown, max = 160): string {
  const text = typeof value === 'string' ? value : JSON.stringify(value)
  return text.length > max ? `${text.slice(0, max - 1)}…` : text
}

function argsText(args: AuditPart['args']): string {
  if (!args || typeof args === 'string') return args ?? ''
  return Object.entries(args)
    .map(([k, v]) => `${k}: ${typeof v === 'string' ? v : JSON.stringify(v)}`)
    .join(' · ')
}

const label = (a: AgentName) => AGENT_INFO[a].label

function blankAgents(): Record<AgentName, AgentState> {
  return Object.fromEntries(
    AGENTS.map((a) => [a, { status: 'idle', activity: 'Standing by', said: null, report: null }]),
  ) as Record<AgentName, AgentState>
}

export function buildRun(runId: string, events: AuditEvent[]): RunView {
  const view: RunView = {
    runId, ticketId: null, startIndex: events[0]?.index ?? 0, finished: false, failed: false, resolved: false,
    agents: blankAgents(), chain: [], active: null, feed: [], order: [],
  }
  const push = (e: AuditEvent, who: FeedItem['who'], kind: FeedKind, text: string, n = 0) =>
    view.feed.push({ key: `${e.index}-${n}`, who, kind, text, time: e.timestamp })

  for (const e of events) {
    const d = e.detail ?? {}
    if (e.agent === 'system') {
      if (e.node === 'run_started') view.ticketId = d.ticket_id ?? null
      if (e.node === 'ticket_resolved') {
        view.resolved = true
        push(e, 'system', 'system', `Ticket ${d.ticket_id} marked resolved.`)
      }
      if (e.node === 'run_finished') {
        view.finished = true
        view.failed = d.status === 'failed'
        if (view.failed) push(e, 'system', 'error', `Run failed: ${d.error}`)
      }
      continue
    }
    if (e.agent === 'human') {
      const by = d.by ? ` by ${d.by}` : ''
      push(e, 'human', 'human', `Payment ${d.decision}${by}.`)
      continue
    }
    if (!isAgent(e.agent)) continue
    const a = e.agent
    const st = view.agents[a]
    if (!view.order.includes(a)) view.order.push(a)
    if (e.chain.length > view.chain.length) view.chain = e.chain
    view.active = a

    switch (e.node) {
      case 'user_prompt': {
        st.status = 'working'
        st.activity = e.delegated_by ? `Picked up a task from ${label(e.delegated_by)}` : 'Picked up the ticket'
        push(e, a, 'task', String(d.prompt ?? ''))
        break
      }
      case 'model_request': {
        st.status = 'thinking'
        st.activity = 'Thinking…'
        ;(d.parts as AuditPart[] | undefined)?.forEach((p, n) => {
          if (p.kind !== 'tool-return' || !p.tool || p.tool === 'delegate' || p.tool === 'final_result') return
          const content = p.content as Record<string, unknown> | undefined
          if (content && typeof content === 'object' && content.status === 'pending_human_approval') {
            push(e, a, 'pending', 'Payment queued for a person to approve.', n)
          } else {
            push(e, a, 'result', `${p.tool} → ${short(p.content)}`, n)
          }
        })
        break
      }
      case 'model_response': {
        const parts = (d.parts as AuditPart[] | undefined) ?? []
        parts.forEach((p, n) => {
          if (p.kind === 'text' && typeof p.content === 'string' && p.content.trim()) {
            st.said = p.content.trim()
            push(e, a, 'say', st.said, n)
          }
          if (p.kind !== 'tool-call' || !p.tool || p.tool === 'final_result') return
          if (p.tool === 'delegate' && p.args && typeof p.args === 'object') {
            const to = String(p.args.to)
            const task = String(p.args.task ?? '')
            st.status = 'waiting'
            st.activity = isAgent(to) ? `Waiting on ${label(to)}` : `Asked ${to}`
            st.said = task
            push(e, a, 'delegate', `→ ${isAgent(to) ? label(to) : to}: ${task}`, n)
          } else {
            st.status = 'working'
            st.activity = toolPhrase(p.tool)
            push(e, a, 'tool', `${toolPhrase(p.tool)}${p.args ? ` (${argsText(p.args)})` : ''}`, n)
          }
        })
        break
      }
      case 'end': {
        st.status = 'done'
        const out = d.output as TaskReport | string | undefined
        st.report = out && typeof out === 'object' ? out : null
        st.activity = 'Finished'
        st.said = st.report?.summary ?? st.said
        push(e, a, 'done', st.report?.summary ?? 'Finished.')
        break
      }
      case 'error': {
        st.status = 'error'
        st.activity = 'Hit a problem'
        push(e, a, 'error', String(d.error ?? 'Error'))
        break
      }
    }
  }
  if (view.finished) view.active = null
  return view
}

/** Every run in the trail, grouped by run_id, oldest first. Runs started before the last reset are dropped. */
export function runsSinceReset(events: AuditEvent[]): RunView[] {
  let lastReset = -1
  for (const e of events) if (e.node === 'database_reset') lastReset = e.index
  const groups = new Map<string, AuditEvent[]>()
  for (const e of events) {
    if (e.index <= lastReset || e.run_id === 'reset') continue
    const list = groups.get(e.run_id) ?? []
    list.push(e)
    groups.set(e.run_id, list)
  }
  return [...groups.entries()]
    .filter(([, list]) => list.some((e) => e.node === 'run_started'))
    .map(([id, list]) => buildRun(id, list))
    .sort((a, b) => a.startIndex - b.startIndex)
}
