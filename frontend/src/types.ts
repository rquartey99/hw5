// Shapes returned by the FastAPI backend (backend/main.py).

export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'
export const AGENTS: AgentName[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: string
  notes: string | null
  created_at: string
  state: 'open' | 'resolved'
}

export interface TaskReport {
  agent: AgentName
  ticket_ids: number[]
  status: 'done' | 'needs_human' | 'blocked' | 'info'
  summary: string
  facts: string[]
  actions_taken: string[]
  needs_human: string[]
}

export interface RunInfo {
  run_id: string
  ticket_id: number
  status: 'running' | 'done' | 'failed'
  started_at: string
  finished_at: string | null
  report: TaskReport | null
  error: string | null
}

export interface AuditPart {
  kind: string
  tool?: string
  tool_call_id?: string | null
  args?: Record<string, unknown> | string
  content?: unknown
}

export interface AuditEvent {
  index: number
  timestamp: string
  run_id: string
  agent: AgentName | 'human' | 'system'
  delegated_by: AgentName | null
  chain: AgentName[]
  depth: number
  step: number
  node: string
  model: string | null
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  detail: Record<string, any>
}

export interface Approval {
  id: string
  status: 'pending' | 'approved' | 'rejected' | 'failed'
  created_at: string
  run_id: string
  requested_by: string
  tool: string
  args: { kind?: 'invoice' | 'lease'; ref_id?: number; amount?: number; account?: string }
  decided_by: string | null
  decided_at: string | null
  result: unknown
  payee: string | null
  ticket_id: number | null
}

export interface Cash {
  name: string
  balance: number
  date: string
}
