import { CheckCircle2, AlertTriangle, AlertOctagon, Clock, CheckSquare } from 'lucide-react'

const STATUS_CONFIG: Record<string, { label: string; cls: string; Icon: any }> = {
  PASS:             { label: 'Low Risk (Pass)',         cls: 'badge badge-pass',    Icon: CheckCircle2 },
  REVIEW:           { label: 'Manual Review Req.',      cls: 'badge badge-review',  Icon: AlertTriangle },
  HIGH_RISK_REVIEW: { label: 'High Risk (Flagged)',     cls: 'badge badge-risk',    Icon: AlertOctagon },
  pending:          { label: 'Queued for Audit',        cls: 'badge badge-pending', Icon: Clock },
  analyzing:        { label: 'Verification In-Flight',  cls: 'badge badge-pending', Icon: Clock },
  PENDING:          { label: 'Queued for Audit',        cls: 'badge badge-pending', Icon: Clock },
  ANALYZING:        { label: 'Verification In-Flight',  cls: 'badge badge-pending', Icon: Clock },
  decided:          { label: 'Decision Recorded',       cls: 'badge badge-decided', Icon: CheckSquare },
  DECIDED:          { label: 'Decision Recorded',       cls: 'badge badge-decided', Icon: CheckSquare },
}

export default function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? {
    label: status.replace(/_/g, ' '),
    cls: 'badge badge-pending',
    Icon: Clock
  }
  const { label, cls, Icon } = cfg

  return (
    <span className={cls}>
      <Icon size={12} strokeWidth={2.2} />
      <span>{label}</span>
    </span>
  )
}
