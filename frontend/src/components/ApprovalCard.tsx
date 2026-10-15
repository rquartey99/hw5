// A pending payment, drawn like a check waiting for a signature.
import { AGENT_INFO } from '../runs'
import type { AgentName, Approval } from '../types'
import { money } from '../format'

interface Props {
  item: Approval
  approver: string
  busy: boolean
  onApprove: () => void
  onReject: () => void
}

export default function ApprovalCard({ item, approver, busy, onApprove, onReject }: Props) {
  const { kind, ref_id, amount, account } = item.args
  const what = kind === 'lease' ? `Rent · lease #${ref_id}` : `Invoice #${ref_id}`
  const who = AGENT_INFO[item.requested_by as AgentName]?.label ?? item.requested_by
  return (
    <article className="check" aria-label={`Payment waiting for approval: ${what}`}>
      <div className="check-top">
        <span className="check-label">Needs your OK</span>
        <span className="check-from">from {account ?? 'checking'}</span>
      </div>
      <div className="check-line">
        <span className="check-pay">Pay to the order of</span>
        <span className="check-payee">{item.payee ?? '—'}</span>
        <span className="check-amount">{amount != null ? money(amount) : '—'}</span>
      </div>
      <div className="check-memo">
        Memo: {what}
        {item.ticket_id ? ` · ticket #${item.ticket_id}` : ''} · requested by {who}
      </div>
      <div className="check-actions">
        <button className="btn btn-ghost" onClick={onReject} disabled={busy || !approver}>Decline</button>
        <button className="btn btn-primary" onClick={onApprove} disabled={busy || !approver}>
          {busy ? 'Signing…' : `Approve as ${approver || '…'}`}
        </button>
      </div>
      {!approver && <p className="check-hint">Type your name next to “Approving as” at the top to sign.</p>}
    </article>
  )
}
