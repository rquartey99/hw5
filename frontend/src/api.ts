// Calls to the backend from Problem 7 (uvicorn main:app --port 8000).
import type { Approval, AuditEvent, Cash, RunInfo, Ticket } from './types'

export const API_BASE = ((import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://127.0.0.1:8000').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + path, { headers: { 'Content-Type': 'application/json' }, ...init })
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = body?.detail
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${res.status})`)
  }
  return body as T
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

export const api = {
  health: () => request<{ status: string; running: boolean }>('/api/health'),
  tickets: () => request<Ticket[]>('/api/tickets'),
  cash: () => request<Cash>('/api/cash'),
  events: (after: number | null) =>
    request<{ events: AuditEvent[]; next: number }>(`/api/events?limit=500${after === null ? '' : `&after=${after}`}`),
  approvals: () => request<Approval[]>('/api/approvals'),
  run: (ticketId: number) => post<{ run_id: string }>(`/api/tickets/${ticketId}/run`, { allow_writes: true }),
  runStatus: (runId: string) => request<RunInfo>(`/api/runs/${runId}`),
  approve: (id: string, approver: string) => post<Approval>(`/api/approvals/${id}/approve`, { approver }),
  reject: (id: string, approver: string) =>
    post<Approval>(`/api/approvals/${id}/reject`, { approver, reason: 'Declined on the desk board' }),
  reset: () => post<{ status: string }>('/api/reset'),
}
