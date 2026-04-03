import Link from 'next/link'

import CollapsibleSection from '@/components/ui/CollapsibleSection'
import SignalBar from '@/components/ui/SignalBar'
import StatusChip from '@/components/ui/StatusChip'
import { toneClass } from '@/components/ui/StatusChip'
import { DetailMemoViewModel, MemoInsightItem, MemoSectionItem, ScoreExplanationItem } from '@/lib/view-models/research'
import { cn } from '@/lib/formatting'

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
            <div className="flex items-start justify-between gap-3">
              <div className="eyebrow">{item.label}</div>
              <span className={cn('text-sm font-medium', item.tone ? toneClass(item.tone) : 'text-[color:var(--text-secondary)]', 'rounded-full border px-2.5 py-1')}>
                {item.value}
              </span>
            </div>
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
              <div className="flex items-start justify-between gap-3">
                <div className="text-sm font-medium text-[color:var(--text-primary)]">{item.title}</div>
                {item.value ? <StatusChip tone={item.tone}>{item.value}</StatusChip> : null}
              </div>
              <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{item.body}</p>
            </div>
          ))
        ) : (
          <p className="text-sm leading-6 text-[color:var(--text-secondary)]">No items available.</p>
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
    <div className="grid gap-3 lg:grid-cols-2">
      {items.map((item, index) => (
        <div key={`${item.title}-${index}`} className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-4">
          <div className="flex flex-wrap items-center gap-2">
            <div className="eyebrow">{item.title}</div>
            {item.score != null ? <StatusChip tone={item.tone ?? 'neutral'}>{item.score.toFixed(1)}</StatusChip> : null}
          </div>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{item.body}</p>
          {item.meta ? <p className="mt-2 text-xs uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{item.meta}</p> : null}
        </div>
      ))}
    </div>
  )
}

export default function ResearchWorkspace({ memo }: { memo: DetailMemoViewModel }) {
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
              <StatusChip tone={memo.primaryTag.tone}>{memo.primaryTag.label}</StatusChip>
              {memo.secondaryTag ? <StatusChip tone={memo.secondaryTag.tone}>{memo.secondaryTag.label}</StatusChip> : null}
            </div>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-[color:var(--text-primary)] sm:text-4xl">{memo.name}</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">{memo.headerSubtitle}</p>
            </div>
          </div>

          <div className="grid min-w-full gap-3 sm:grid-cols-3 xl:min-w-[380px] xl:max-w-[420px]">
            <div className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-4">
              <div className="eyebrow">Score</div>
              <div className="mt-2 text-2xl font-semibold tracking-tight text-[color:var(--text-primary)]">{memo.scoreLabel}</div>
            </div>
            <div className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-4">
              <div className="eyebrow">Rank</div>
              <div className="mt-2 text-2xl font-semibold tracking-tight text-[color:var(--text-primary)]">{memo.rankLabel}</div>
            </div>
            <div className="rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-4">
              <div className="eyebrow">Model</div>
              <div className="mt-2 text-lg font-semibold tracking-tight text-[color:var(--text-primary)]">{memo.modelLabel}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="surface-panel p-5 sm:p-6">
        <div className="section-title">Executive Summary</div>
        <div className="mt-4 grid gap-x-8 gap-y-5 md:grid-cols-2">
          {memo.executiveSummary.map((item) => (
            <div key={item.label} className="border-b border-[color:var(--border-subtle)] pb-4 last:border-b-0 md:last:border-b md:[&:nth-last-child(-n+2)]:border-b-0 md:[&:nth-last-child(-n+2)]:pb-0">
              <div className="eyebrow">{item.label}</div>
              <p className="mt-2 text-base leading-7 text-[color:var(--text-primary)]">{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="surface-panel p-5 sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <div className="section-title">Primary Signals</div>
          <div className="eyebrow">Quality, opportunity, risk, confidence</div>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {memo.signals.map((signal) => (
            <SignalBar key={signal.key} signal={signal} />
          ))}
        </div>
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

      <div className="grid gap-6 xl:grid-cols-2">
        <InsightGrid title="Market Structure" items={memo.marketStructure} />
        <InsightGrid title="Evidence And Reliability" items={memo.evidenceItems} />
      </div>

      <section className="surface-panel p-5 sm:p-6">
        <div className="section-title">Score Explanation</div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">
          The score still anchors the page, but the explanation is limited to the clearest supports and drags.
        </p>
        <div className="mt-5 grid gap-6 xl:grid-cols-2">
          <ScoreList title="Top 3 Supports" items={memo.topSupports} />
          <ScoreList title="Top 3 Drags" items={memo.topDrags} />
        </div>
      </section>

      <CollapsibleSection
        title="Deep Diagnostics"
        subtitle="Stress behavior, confidence internals, block scores, and raw context remain available but stay out of the main reading flow."
        defaultOpen={false}
      >
        <div className="space-y-6">
          <div>
            <div className="section-title">Stress Snapshot</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.stressItems} empty="No stress outputs are available." />
            </div>
          </div>

          <div>
            <div className="section-title">Stress Scenarios</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.scenarioItems} empty="No stress scenarios were emitted for this subnet." />
            </div>
          </div>

          <div>
            <div className="section-title">Confidence Breakdown</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.confidenceHeadline.map((item) => ({ title: item.label, body: item.value, tone: item.tone, meta: item.meta }))} empty="No confidence headline is available." />
            </div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.confidenceItems} empty="No confidence breakdown is available." />
            </div>
          </div>

          <div>
            <div className="section-title">Breakers And Drags</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.breaks} empty="No breakers were emitted for this subnet." />
            </div>
          </div>

          <div>
            <div className="section-title">Block Scores</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.blockScores} empty="No block scores are available." />
            </div>
          </div>

          <div>
            <div className="section-title">Visibility And Conditioning</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.visibilityItems} empty="No visibility diagnostics are available." />
            </div>
          </div>

          <div>
            <div className="section-title">Key Uncertainties</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.uncertainties} empty="No key uncertainties were emitted for this subnet." />
            </div>
          </div>

          <div>
            <div className="section-title">Raw Context</div>
            <div className="mt-3">
              <DiagnosticGrid items={memo.rawContext} empty="No raw context values are available." />
            </div>
          </div>

          {memo.links.length ? (
            <div>
              <div className="section-title">External Links</div>
              <div className="mt-3 flex flex-wrap gap-3">
                {memo.links.map((link) => (
                  <a key={link.href} href={link.href} target="_blank" rel="noreferrer" className="button-secondary">
                    {link.label}
                  </a>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </CollapsibleSection>
    </div>
  )
}
