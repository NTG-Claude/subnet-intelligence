import { RowFlag, SignalTone } from '@/lib/view-models/research'

import StatusChip from './StatusChip'

function severityTone(flags: RowFlag[], awaitingRun: boolean): { label: string; tone: SignalTone } {
  if (awaitingRun) return { label: 'Awaiting Run', tone: 'warning' }
  if (flags.some((flag) => flag.label === 'Stale run')) return { label: 'Stale', tone: 'warning' }
  if (flags.some((flag) => flag.label === 'Incomplete telemetry')) return { label: 'Low Trust', tone: 'fragility' }
  if (flags.some((flag) => flag.label === 'Reconstructed inputs')) return { label: 'Review', tone: 'warning' }
  if (flags.some((flag) => flag.label === 'Low confidence')) return { label: 'Usable', tone: 'confidence' }
  return { label: 'Trusted', tone: 'quality' }
}

export default function TrustBadge({
  flags,
  awaitingRun,
}: {
  flags: RowFlag[]
  awaitingRun: boolean
}) {
  const primary = severityTone(flags, awaitingRun)

  return (
    <div className="flex flex-wrap items-center gap-2">
      <StatusChip tone={primary.tone}>{primary.label}</StatusChip>
      {flags
        .filter((flag) => flag.label !== primary.label)
        .slice(0, 2)
        .map((flag) => (
          <StatusChip key={flag.label} tone={flag.tone}>
            {flag.label}
          </StatusChip>
        ))}
    </div>
  )
}
