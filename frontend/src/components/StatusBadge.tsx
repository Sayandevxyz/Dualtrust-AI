import { CheckCircle, AlertTriangle, XCircle, Clock, CheckSquare } from 'lucide-react'

const STATUS_CONFIG: Record<string, { label: string; cls: string; Icon: any }> = {
  PASS:             { label: 'Pass',           cls: 'badge badge-pass',    Icon: CheckCircle },
  REVIEW:           { label: 'Review',         cls: 'badge badge-review',  Icon: AlertTriangle },
  HIGH_RISK_REVIEW: { label: 'High Risk',      cls: 'badge badge-risk',    Icon: XCircle },
  pending:          { label: 'Pending',         cls: 'badge badge-pending', Icon: Clock },
  analyzing:        { label: 'Analyzing...',   cls: 'badge badge-pending', Icon: Clock },
  decided:          { label: 'Decided',        cls: 'badge badge-decided', Icon: CheckSquare },
}

export default function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG['pending']
  const { label, cls, Icon } = cfg
  return (
    <span className={cls}>
      <Icon size={11} />
      {label}
    </span>
  )
}
