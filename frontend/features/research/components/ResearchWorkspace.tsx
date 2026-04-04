import Link from 'next/link'

import SignalBar from '@/components/ui/SignalBar'
import StatusChip from '@/components/ui/StatusChip'
import { SubnetSignalHistoryPoint } from '@/lib/api'
import { DetailMemoViewModel } from '@/lib/view-models/research'

import IndicatorStack from './IndicatorStack'
import PrimarySignalsTrend from './PrimarySignalsTrend'

function CompactStat({
  label,
  value,
  detail,
}: {
  label: string
  value: string
  detail?: string
}) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[color:rgba(148,163,184,0.12)] bg-[linear-gradient(180deg,rgba(20,31,43,0.92),rgba(16,27,39,0.96))] px-5 py-4">
      <div className="eyebrow">{label}</div>
      <div className="mt-3 text-[2rem] font-semibold leading-none tracking-tight text-[color:var(--text-primary)]">{value}</div>
      {detail ? <div className="mt-3 text-sm font-medium text-[color:var(--text-secondary)]">{detail}</div> : null}
    </div>
  )
}
export default function ResearchWorkspace({
  memo,
  netuid,
  initialSignalHistory,
}: {
  memo: DetailMemoViewModel
  netuid: number
  initialSignalHistory?: SubnetSignalHistoryPoint[] | null
}) {
  return (
    <div className="space-y-6 pb-12">
      <Link href="/" className="button-secondary">
        Back to discover
      </Link>

      <section className="surface-panel overflow-hidden p-5 sm:p-6">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px] xl:items-end">
          <div className="min-w-0 space-y-4">
            <div className="flex flex-wrap items-center gap-2.5">
              <StatusChip tone="neutral">{memo.netuidLabel}</StatusChip>
            </div>
            <div className="space-y-3">
              <div className="min-w-0">
                <h1 className="text-4xl font-semibold tracking-tight text-[color:var(--text-primary)] sm:text-[3.4rem] sm:leading-[0.95]">{memo.name}</h1>
                <div className="mt-3 text-sm font-medium text-[color:var(--text-tertiary)]">Updated {memo.updatedLabel}</div>
              </div>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <CompactStat label="Score" value={memo.scoreLabel} />
            <CompactStat label="Rank" value={memo.rankLabel} detail={memo.percentileLabel === 'n/a' ? undefined : memo.percentileLabel} />
          </div>
        </div>

        <div className="mt-6 border-t border-[color:rgba(148,163,184,0.12)] pt-5">
          <div className="flex items-center justify-between gap-4">
            <div className="section-title">Primary Signals</div>
          </div>
          <div className="mt-4 grid gap-3 xl:grid-cols-4">
            {memo.signals.map((signal) => (
              <SignalBar key={signal.key} signal={signal} compact />
            ))}
          </div>
        </div>
      </section>

      <section className="surface-panel p-5 sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <div className="section-title">Signal Trend</div>
          <div className="eyebrow">Primary score history</div>
        </div>
        <PrimarySignalsTrend netuid={netuid} initialPoints={initialSignalHistory} />
      </section>

      <section className="space-y-3">
        <div>
          <div className="section-title">Indicator Stack</div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">
            Compact thesis-facing indicators across quality, opportunity, risk, and confidence. Each row is expressed as desirability for the investment case.
          </p>
        </div>
        <IndicatorStack categories={memo.indicatorStack} />
      </section>
    </div>
  )
}
