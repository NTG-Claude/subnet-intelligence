import Link from 'next/link'

import CollapsibleSection from '@/components/ui/CollapsibleSection'
import SignalBar from '@/components/ui/SignalBar'
import StatusChip from '@/components/ui/StatusChip'
import { SubnetSignalHistoryPoint } from '@/lib/api'
import { DetailMemoViewModel, MemoSectionItem } from '@/lib/view-models/research'

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
    <div className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-4">
      <div className="eyebrow">{label}</div>
      <div className="mt-2 text-xl font-semibold tracking-tight text-[color:var(--text-primary)]">{value}</div>
      {detail ? <div className="mt-1.5 text-sm text-[color:var(--text-secondary)]">{detail}</div> : null}
    </div>
  )
}

function DiagnosticGrid({
  items,
  empty,
  showMeta = true,
}: {
  items: MemoSectionItem[]
  empty: string
  showMeta?: boolean
}) {
  if (!items.length) {
    return <p className="text-sm leading-6 text-[color:var(--text-secondary)]">{empty}</p>
  }

  return (
    <div className="grid gap-2.5 lg:grid-cols-2">
      {items.map((item, index) => (
        <div key={`${item.title}-${index}`} className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-3.5">
          <div className="eyebrow">{item.title}</div>
          <p className="mt-1.5 text-sm leading-5 text-[color:var(--text-secondary)]">{item.body}</p>
          {showMeta && item.meta ? <p className="mt-1 text-xs text-[color:var(--text-tertiary)]">{item.meta}</p> : null}
        </div>
      ))}
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
  const evidenceSummary = memo.evidenceItems[0]?.body ?? 'Trust details are not available yet.'

  return (
    <div className="space-y-6 pb-12">
      <Link href="/" className="button-secondary">
        Back to discover
      </Link>

      <section className="surface-panel p-5 sm:p-6">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_320px]">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip tone="neutral">{memo.netuidLabel}</StatusChip>
            </div>
            <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
              <div className="min-w-0">
                <h1 className="text-3xl font-semibold tracking-tight text-[color:var(--text-primary)] sm:text-4xl">{memo.name}</h1>
                <div className="mt-2 text-sm text-[color:var(--text-tertiary)]">Updated {memo.updatedLabel}</div>
              </div>
              <div className="grid w-full gap-3 sm:grid-cols-2 xl:w-auto xl:min-w-[320px]">
                <CompactStat label="Score" value={memo.scoreLabel} />
                <CompactStat label="Rank" value={memo.rankLabel} detail={memo.percentileLabel === 'n/a' ? undefined : memo.percentileLabel} />
              </div>
            </div>
          </div>

          <div className="xl:pl-2">
            <div className="section-title">Primary Signals</div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              {memo.signals.map((signal) => (
                <SignalBar key={signal.key} signal={signal} compact />
              ))}
            </div>
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

      <CollapsibleSection
        title="Deep Diagnostics"
        subtitle="Secondary trust, structure, stress, and scoring detail."
        defaultOpen={false}
      >
        <div className="space-y-6">
          <div>
            <div className="section-title">Trust & Evidence</div>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">{evidenceSummary}</p>
            <div className="mt-3">
              <DiagnosticGrid
                items={[
                  ...memo.confidenceItems,
                  ...memo.visibilityItems,
                  ...memo.uncertainties,
                ]}
                empty="No trust details are available yet."
              />
            </div>
          </div>

          <div>
            <div className="section-title">Market Structure</div>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">{memo.researchSummary.relativePeerContext}</p>
            <div className="mt-3 grid gap-2.5 lg:grid-cols-2">
              {memo.marketStructure.length ? (
                memo.marketStructure.map((item) => (
                  <div key={item.label} className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-3.5">
                    <div className="eyebrow">{item.label}</div>
                    <div className="mt-1.5 text-sm font-medium text-[color:var(--text-primary)]">{item.value}</div>
                    <p className="mt-1.5 text-sm leading-5 text-[color:var(--text-secondary)]">{item.body}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm leading-6 text-[color:var(--text-secondary)]">No market-structure detail is available.</p>
              )}
            </div>
          </div>

          <div>
            <div className="section-title">Stress View</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.stressItems} empty="No stress outputs are available." />
            </div>
          </div>

          <div>
            <div className="section-title">Scenario Losses</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.scenarioItems} empty="No stress scenarios were emitted for this subnet." />
            </div>
          </div>

          <div>
            <div className="section-title">Score Pillars</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.blockScores} empty="No score pillar data is available." />
            </div>
          </div>

          <div>
            <div className="section-title">Input Checks</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.visibilityItems} empty="No input-check diagnostics are available." />
            </div>
          </div>
        </div>
      </CollapsibleSection>
    </div>
  )
}
