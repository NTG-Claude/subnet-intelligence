import Link from 'next/link'

import CollapsibleSection from '@/components/ui/CollapsibleSection'
import SignalBar from '@/components/ui/SignalBar'
import StatusChip from '@/components/ui/StatusChip'
import { DetailMemoViewModel, MemoInsightItem, MemoSectionItem, ScoreExplanationItem } from '@/lib/view-models/research'
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
      {detail ? <p className="mt-1.5 text-sm leading-6 text-[color:var(--text-secondary)]">{detail}</p> : null}
    </div>
  )
}

function InsightGrid({
  title,
  intro,
  items,
}: {
  title: string
  intro?: string
  items: MemoInsightItem[]
}) {
  return (
    <section className="surface-panel p-5 sm:p-6">
      <div className="section-title">{title}</div>
      {intro ? <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">{intro}</p> : null}
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {items.map((item) => (
          <div key={item.label} className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-4">
            <div className="eyebrow">{item.label}</div>
            <div className="mt-2 text-sm font-medium text-[color:var(--text-primary)]">{item.value}</div>
            <p className="mt-2 max-w-[54ch] text-sm leading-6 text-[color:var(--text-secondary)]">{item.body}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function ExplanationList({
  title,
  intro,
  items,
  empty,
}: {
  title: string
  intro?: string
  items: ScoreExplanationItem[]
  empty: string
}) {
  return (
    <section className="surface-panel p-5 sm:p-6">
      <div className="section-title">{title}</div>
      {intro ? <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">{intro}</p> : null}
      <div className="mt-4 space-y-3">
        {items.length ? (
          items.map((item) => (
            <div key={`${title}-${item.title}`} className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-4">
              <div className="text-sm font-medium text-[color:var(--text-primary)]">{item.title}</div>
              <p className="mt-1.5 text-sm leading-6 text-[color:var(--text-secondary)]">{item.body}</p>
            </div>
          ))
        ) : (
          <p className="text-sm leading-6 text-[color:var(--text-secondary)]">{empty}</p>
        )}
      </div>
    </section>
  )
}

function DiagnosticGrid({
  items,
  empty,
}: {
  items: MemoSectionItem[]
  empty: string
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
          {item.meta ? <p className="mt-1 text-xs text-[color:var(--text-tertiary)]">{item.meta}</p> : null}
        </div>
      ))}
    </div>
  )
}

function DetailList({
  title,
  intro,
  items,
  empty,
}: {
  title: string
  intro?: string
  items: MemoSectionItem[]
  empty: string
}) {
  return (
    <section className="surface-panel p-5 sm:p-6">
      <div className="section-title">{title}</div>
      {intro ? <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">{intro}</p> : null}
      <div className="mt-4">
        <DiagnosticGrid items={items} empty={empty} />
      </div>
    </section>
  )
}

function uniqueSectionItems(items: MemoSectionItem[]): MemoSectionItem[] {
  const seen = new Set<string>()

  return items.filter((item) => {
    const key = `${item.title}::${item.body}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

export default function ResearchWorkspace({
  memo,
  netuid,
}: {
  memo: DetailMemoViewModel
  netuid: number
}) {
  const verdict = memo.headerSubtitle || memo.researchSummary.setupRead
  const strongestSupport = memo.anchorInsights.find((item) => item.label === 'Strongest support')?.value ?? 'No clear support stands out yet.'
  const mainLimiter = memo.anchorInsights.find((item) => item.label === 'Main thing capping the score')?.value ?? 'No single limitation dominates yet.'
  const trustSummary = memo.evidenceItems[0]?.body ?? 'Trust details are not available yet.'
  const trustLabel =
    memo.secondaryTag?.label ??
    memo.contextRow.find((item) => item.label === 'Read Trust')?.value ??
    'Trust not available'

  const riskItems = uniqueSectionItems([
    ...memo.topDrags.map((item) => ({ title: item.title, body: item.body, tone: item.tone })),
    ...memo.breaks,
    ...memo.uncertainties,
  ])

  const trustItems = uniqueSectionItems([
    ...memo.evidenceItems.map((item) => ({
      title: item.label,
      body: item.body,
      tone: item.tone,
      meta: item.value,
    })),
    ...memo.confidenceHeadline.map((item) => ({
      title: item.label,
      body: item.meta ? `${item.value}. ${item.meta}` : item.value,
      tone: item.tone,
    })),
    ...memo.confidenceItems,
    ...memo.visibilityItems,
  ])

  return (
    <div className="space-y-6 pb-12">
      <Link href="/" className="button-secondary">
        Back to discover
      </Link>

      <section className="surface-panel p-5 sm:p-6">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0 space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip tone="neutral">{memo.netuidLabel}</StatusChip>
            </div>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-[color:var(--text-primary)] sm:text-4xl">{memo.name}</h1>
              <p className="mt-2 max-w-3xl text-base leading-7 text-[color:var(--text-primary)]">{verdict}</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] px-3.5 py-3">
                  <div className="eyebrow">Biggest positive driver</div>
                  <p className="mt-1.5 text-sm leading-6 text-[color:var(--text-primary)]">{strongestSupport}</p>
                </div>
                <div className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] px-3.5 py-3">
                  <div className="eyebrow">Biggest limiting factor</div>
                  <p className="mt-1.5 text-sm leading-6 text-[color:var(--text-primary)]">{mainLimiter}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid min-w-full gap-3 sm:grid-cols-2 xl:min-w-[420px] xl:max-w-[460px]">
            <CompactStat label="Score" value={memo.scoreLabel} />
            <CompactStat label="Rank" value={memo.rankLabel} />
            <CompactStat label="Confidence" value={trustLabel} detail={trustSummary} />
            <CompactStat label="Last updated" value={memo.updatedLabel} />
          </div>
        </div>
      </section>

      <section className="surface-panel p-5 sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <div className="section-title">Primary Signals</div>
          <div className="eyebrow">Higher is better, except risk</div>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {memo.signals.map((signal) => (
            <SignalBar key={signal.key} signal={signal} />
          ))}
        </div>
        <PrimarySignalsTrend netuid={netuid} />
      </section>

      <ExplanationList
        title="What supports the case"
        intro={memo.researchSummary.whyNow}
        items={memo.topSupports}
        empty="No clear support stands out yet."
      />

      <DetailList
        title="What could break the case"
        intro={`${memo.researchSummary.mainConstraint} ${memo.researchSummary.breakCondition}`}
        items={riskItems}
        empty="No single risk dominates yet."
      />

      <DetailList
        title="How much to trust this read"
        intro={trustSummary}
        items={trustItems}
        empty="No trust details are available yet."
      />

      <InsightGrid
        title="How the market is set up"
        intro={memo.researchSummary.relativePeerContext}
        items={memo.marketStructure}
      />

      <CollapsibleSection
        title="Deep Diagnostics"
        subtitle="Lower-level stress, scenario, and scoring detail for deeper review."
        defaultOpen={false}
      >
        <div className="space-y-6">
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
