import Link from 'next/link'

import CollapsibleSection from '@/components/ui/CollapsibleSection'
import SignalBar from '@/components/ui/SignalBar'
import StatusChip from '@/components/ui/StatusChip'
import { DetailMemoViewModel, MemoInsightItem, MemoSectionItem, ScoreExplanationItem } from '@/lib/view-models/research'
import PrimarySignalsTrend from './PrimarySignalsTrend'

function InsightGrid({
  title,
  items,
}: {
  title: string
  items: MemoInsightItem[]
}) {
  return (
    <section className="surface-panel p-5 sm:p-6">
      <div className="section-title">{title}</div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {items.map((item) => (
          <div key={item.label} className="border-b border-[color:var(--border-subtle)] pb-4 last:border-b-0 last:pb-0">
            <div className="eyebrow">{item.label}</div>
            <p className="mt-2 max-w-[54ch] text-sm leading-6 text-[color:var(--text-secondary)]">{item.body}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function ScoreList({
  title,
  items,
}: {
  title: string
  items: ScoreExplanationItem[]
}) {
  return (
    <div>
      <div className="eyebrow">{title}</div>
      <div className="mt-3 space-y-3">
        {items.length ? (
          items.map((item) => (
            <div key={`${title}-${item.title}`} className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-4">
              <div className="text-sm font-medium text-[color:var(--text-primary)]">{item.title}</div>
              <p className="mt-1.5 text-sm leading-6 text-[color:var(--text-secondary)]">{item.body}</p>
            </div>
          ))
        ) : (
          <p className="text-sm leading-6 text-[color:var(--text-secondary)]">No clear items are available.</p>
        )}
      </div>
    </div>
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

export default function ResearchWorkspace({
  memo,
  netuid,
}: {
  memo: DetailMemoViewModel
  netuid: number
}) {
  return (
    <div className="space-y-6 pb-12">
      <Link href="/" className="button-secondary">
        Back to discover
      </Link>

      <section className="surface-panel p-5 sm:p-6">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip tone="neutral">{memo.netuidLabel}</StatusChip>
            </div>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-[color:var(--text-primary)] sm:text-4xl">{memo.name}</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">{memo.headerSubtitle}</p>
              <div className="mt-4 grid gap-3 lg:grid-cols-2">
                <div className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] px-3.5 py-3">
                  <div className="eyebrow">Why This Score</div>
                  <p className="mt-1.5 text-sm leading-6 text-[color:var(--text-primary)]">{memo.researchSummary.setupRead}</p>
                </div>
                <div className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] px-3.5 py-3">
                  <div className="eyebrow">How Much To Trust This Read</div>
                  <p className="mt-1.5 text-sm leading-6 text-[color:var(--text-primary)]">{memo.evidenceItems[0]?.body ?? 'Trust details are not available yet.'}</p>
                </div>
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {memo.anchorInsights.map((item) => (
                  <div key={item.label} className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] px-3.5 py-3">
                    <div className="eyebrow">{item.label}</div>
                    <p className="mt-1.5 text-sm leading-6 text-[color:var(--text-primary)]">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid min-w-full gap-3 sm:grid-cols-2 xl:min-w-[380px] xl:max-w-[420px]">
            <div className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-4">
              <div className="eyebrow">Score</div>
              <div className="mt-2 text-2xl font-semibold tracking-tight text-[color:var(--text-primary)]">{memo.scoreLabel}</div>
            </div>
            <div className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-4">
              <div className="eyebrow">Rank</div>
              <div className="mt-2 text-2xl font-semibold tracking-tight text-[color:var(--text-primary)]">{memo.rankLabel}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="surface-panel p-5 sm:p-6">
        <div className="section-title">Decision Summary</div>
        <div className="mt-4 grid gap-x-8 gap-y-5 md:grid-cols-2">
          {memo.executiveSummary.map((item) => (
            <div key={item.label} className="border-b border-[color:var(--border-subtle)] pb-4 last:border-b-0 md:last:border-b md:[&:nth-last-child(-n+2)]:border-b-0 md:[&:nth-last-child(-n+2)]:pb-0">
              <div className="eyebrow">{item.label}</div>
              <p className="mt-2 text-base leading-7 text-[color:var(--text-primary)]">{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <InsightGrid title="Evidence & Trust" items={memo.evidenceItems} />
        <InsightGrid title="Market Structure" items={memo.marketStructure} />
      </div>

      <section className="surface-panel p-5 sm:p-6">
        <div className="section-title">Why The Score Lands Here</div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">
          These are the clearest reasons the score holds up where it does, and the clearest reasons it is not higher.
        </p>
        <div className="mt-5 grid gap-6 xl:grid-cols-2">
          <ScoreList title="What Is Supporting The Score" items={memo.topSupports} />
          <ScoreList title="What Is Capping The Score" items={memo.topDrags} />
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

      <section className="surface-panel p-5 sm:p-6">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {memo.contextRow.map((item) => (
            <div key={item.label} className="border-b border-[color:var(--border-subtle)] pb-3 sm:border-b-0 sm:pb-0 sm:pr-3 sm:[&:not(:last-child)]:border-r sm:[&:not(:last-child)]:border-[color:var(--border-subtle)]">
              <div className="eyebrow">{item.label}</div>
              <div className="mt-2 text-base font-medium text-[color:var(--text-primary)]">{item.value}</div>
            </div>
          ))}
        </div>
      </section>

      <CollapsibleSection
        title="Deep Diagnostics"
        subtitle="Reference checks for stress, inputs, and scoring."
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
            <div className="section-title">Conviction Breakdown</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.confidenceHeadline.map((item) => ({ title: item.label, body: item.value, tone: item.tone, meta: item.meta }))} empty="No conviction summary is available." />
            </div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.confidenceItems} empty="No conviction breakdown is available." />
            </div>
          </div>

          <div>
            <div className="section-title">Failure Points</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.breaks} empty="No failure points were emitted for this subnet." />
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

          <div>
            <div className="section-title">Key Uncertainties</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.uncertainties} empty="No key uncertainties were emitted for this subnet." />
            </div>
          </div>

        </div>
      </CollapsibleSection>
    </div>
  )
}
