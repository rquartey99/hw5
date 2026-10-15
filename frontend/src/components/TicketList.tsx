import type { Ticket } from '../types'

const TYPE_LABEL: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Price override',
}

function detail(t: Ticket): string {
  if (t.sku) return `${t.qty ?? ''} × ${t.sku}${t.size ? ` · ${t.size}` : ''}`
  if (t.lease_id) return `Lease #${t.lease_id}`
  return t.type
}

interface Props {
  tickets: Ticket[]
  selectedId: number | null
  runningTicketId: number | null
  onSelect: (id: number) => void
}

export default function TicketList({ tickets, selectedId, runningTicketId, onSelect }: Props) {
  return (
    <aside className="tickets" aria-label="Tickets">
      <h2 className="section-title">Tickets</h2>
      <ul>
        {tickets.map((t) => {
          const running = runningTicketId === t.id
          return (
            <li key={t.id}>
              <button
                className={`ticket-card${selectedId === t.id ? ' selected' : ''}${t.state === 'resolved' ? ' resolved' : ''}`}
                onClick={() => onSelect(t.id)}
                aria-pressed={selectedId === t.id}
              >
                <span className="ticket-top">
                  <span className="ticket-id">#{t.id}</span>
                  <span className={`pill ${running ? 'pill-running' : t.state === 'resolved' ? 'pill-resolved' : 'pill-open'}`}>
                    {running ? 'Team working' : t.state === 'resolved' ? 'Resolved' : 'Open'}
                  </span>
                </span>
                <span className="ticket-subject">{t.subject}</span>
                <span className="ticket-meta">{TYPE_LABEL[t.type] ?? t.type} · {t.requester}</span>
                <span className="ticket-meta mono">{detail(t)}</span>
                {t.state === 'resolved' && <span className="stamp" aria-hidden="true">Resolved</span>}
              </button>
            </li>
          )
        })}
      </ul>
    </aside>
  )
}
