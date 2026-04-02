'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'

import PageHeader from '@/components/ui/PageHeader'
import StatusChip, { toneClass } from '@/components/ui/StatusChip'
import MetricCard from '@/components/ui/MetricCard'
import SignalBar from '@/components/ui/SignalBar'
import TrustBadge from '@/components/ui/TrustBadge'
import { cn } from '@/lib/formatting'
import { DetailMemoViewModel, MemoSectionItem, SignalStat } from '@/lib/view-models/research'

function parseMetricValue(value: string): number | null {
  const match = value.match(/-?\d+(\.\d+)?/)
  if (!match) return null
  return Number.parseFloat(match[0])
}

function highlightLabel(values: Array<number | null>, index: number, inverse = false): string | null {
  const numeric = values.filter((value): value is number => value != null)
  if (numeric.length < 2 || values[index] == null) return null
  const target = values[index] as number
  const best = inverse ? Math.min(...numeric) : Math.max(...numeric)
  const worst = inverse ? Math.max(...numeric) : Math.min(...numeric)
  if (target === best && target !== worst) return 'Best'
  if (target === worst && target !== best) return inverse ? 'Most Fragile' : 'Weakest'
  return null
}

function matrixSectionTitle(title: string, subtitle: string) {
  return (
    <div className="mb-4">
      <div className="section-title">{title}</div>
      <p className="mt-1 text-sm text-[color:var(--text-secondary)]">{subtitle}</p>
    </div>
  )
}

function compareGridClass(count: number): string {
  if (count === 2) return 'xl:grid-cols-2'
  if (count === 3) return 'xl:grid-cols-3'
  return 'xl:grid-cols-4'
}

function trustComparisonLabel(values: Array<number | null>, index: number, inverse = false): string | null {
  const numeric = values.filter((value): value is number => value != null)
  if (numeric.length < 2 || values[index] == null) return null
  const target = values[index] as number
  const best = inverse ? Math.min(...numeric) : Math.max(...numeric)
  const worst = inverse ? Math.max(...numeric) : Math.min(...numeric)
  if (target === best && target !== worst) return inverse ? 'Cleanest' : 'Strongest'
  if (target === worst && target !== best) return inverse ? 'Most Incomplete' : 'Weakest'
  return null
}

function InsightColumn({ title, items, empty }: { title: string; items: MemoSectionItem[]; empty: string }) {
  return (
    <div className="space-y-3">
      <div className="eyebrow">{title}</div>
      {items.length ? (
        items.slice(0, 4).map((item, index) => (
          <div key={`${item.title}-${index}`} className="surface-subtle p-3">
            <div className="text-sm font-medium text-[color:var(--text-primary)]">{item.title}</div>
            <div className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{item.body}</div>
            {item.meta ? <div className="mt-2 text-xs uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{item.meta}</div> : null}
          </div>
        ))
      ) : (
        <div className="surface-subtle p-3 text-sm text-[color:var(--text-tertiary)]">{empty}</div>
      )}
    </div>
  )
}

export default function CompareWorkspace({ memos }: { memos: DetailMemoViewModel[] }) {
  const [differencesOnly, setDifferencesOnly] = useState(false)

  const signalRows = useMemo(
    () =>
      ['fundamental_quality', 'mispricing_signal', 'fragility_risk', 'signal_confidence']
        .map((key) => ({
          label: memos[0]?.signals.find((signal) => signal.key === key)?.label ?? key,
          inverse: key === 'fragility_risk',
          values: memos.map((memo) => memo.signals.find((signal) => signal.key === key) ?? null),
        }))
        .filter((row) =>
          differencesOnly
            ? new Set(row.values.map((value) => value?.value?.toFixed(1) ?? 'na')).size > 1
            : true,
        ),
    [differencesOnly, memos],
  )

  const trustRows = useMemo(
    () => {
      const keys = ['Signal confidence', 'Data confidence', 'Market confidence', 'Thesis confidence', 'Reconstructed inputs', 'Discarded inputs']
      return keys
        .map((label) => ({
          label,
          values: memos.map((memo) => {
            const source = [...memo.confidenceHeadline, ...memo.visibilityItems.map((item) => ({ label: item.title, value: item.body, tone: item.tone }))]
            return source.find((item) => item.label === label || item.label === label.replace('inputs', 'Inputs') || item.label === label.replace('confidence', 'confidence')) ?? null
          }),
        }))
        .filter((row) =>
          differencesOnly
            ? new Set(row.values.map((value) => value?.value ?? 'na')).size > 1
            : true,
        )
    },
    [differencesOnly, memos],
  )

  return (
    <div className="space-y-6 pb-16">
      <PageHeader
        title="Compare subnets"
        subtitle="Use aligned metrics to determine which names are strongest, weakest, most fragile, or least trustworthy before you spend time on the full memo."
        actions={
          <>
            <Link href="/" className="button-secondary">
              Back to discover
            </Link>
            <button type="button" onClick={() => setDifferencesOnly((current) => !current)} className={cn('button-secondary', differencesOnly && 'border-[color:var(--confidence-border)] bg-[color:var(--confidence-surface)] text-[color:var(--confidence-strong)]')}>
              Highlight differences only
            </button>
          </>
        }
      />

      <section className="surface-panel p-5 sm:p-6">
        {matrixSectionTitle('Summary', 'Compare the decision framing, overall rank, and current trust state before drilling into individual metrics.')}
        <div className={cn('grid gap-4', compareGridClass(memos.length))}>
          {memos.map((memo) => (
            <div key={memo.netuidLabel} className="surface-subtle p-4">
              <div className="flex flex-wrap items-center gap-2">
                <StatusChip tone="neutral">{memo.netuidLabel}</StatusChip>
                <StatusChip tone={memo.modelLabelTone}>{memo.modelLabel}</StatusChip>
              </div>
              <Link href={memo.href} className="mt-3 block text-2xl font-semibold tracking-tight text-[color:var(--text-primary)] hover:text-[color:var(--mispricing-strong)]">
                {memo.name}
              </Link>
              <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{memo.decisionLine}</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <MetricCard label="Rank" value={memo.rankLabel} />
                <MetricCard label="Percentile" value={memo.percentileLabel} />
                <MetricCard label="Updated" value={memo.updatedLabel} />
                <MetricCard label="Trust" value={<TrustBadge flags={memo.summaryFlags} awaitingRun={memo.awaitingRun} />} />
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="surface-panel p-5 sm:p-6">
        {matrixSectionTitle('Signal Comparison', 'Aligned signal bars emphasize strongest quality, biggest mispricing, lowest fragility, and strongest confidence.')}
        <div className="space-y-6">
          {signalRows.map((row) => {
            const values = row.values.map((item) => item?.value ?? null)
            return (
              <div key={row.label} className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="section-title text-base">{row.label}</div>
                  {row.inverse ? <span className="text-xs text-[color:var(--text-tertiary)]">Lower is better</span> : null}
                </div>
                <div className={cn('grid gap-4', compareGridClass(memos.length))}>
                  {row.values.map((signal, index) => (
                    <div key={`${memos[index].netuidLabel}-${row.label}`} className="surface-subtle p-4">
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <div className="text-sm font-medium text-[color:var(--text-primary)]">{memos[index].name}</div>
                        {highlightLabel(values, index, row.inverse) ? (
                          <span className={cn('rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.18em]', toneClass(row.inverse ? 'fragility' : 'quality'))}>
                            {highlightLabel(values, index, row.inverse)}
                          </span>
                        ) : null}
                      </div>
                      {signal ? <SignalBar signal={signal as SignalStat} /> : <div className="surface-subtle p-3 text-sm text-[color:var(--text-tertiary)]">No score available.</div>}
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </section>

      <section className="surface-panel p-5 sm:p-6">
        {matrixSectionTitle('Trust Comparison', 'Trust matters as much as upside. This section calls out confidence strength, repaired telemetry, discarded inputs, and stale or incomplete evidence.')}
        <div className="space-y-4">
          {trustRows.map((row) => {
            const values = row.values.map((item) => parseMetricValue(item?.value ?? ''))
            return (
              <div key={row.label} className="space-y-3 border-t border-[color:var(--border-subtle)] pt-4 first:border-t-0 first:pt-0">
                <div className="text-sm font-medium text-[color:var(--text-primary)]">{row.label}</div>
                <div className={cn('grid gap-4', compareGridClass(memos.length))}>
                  {memos.map((memo, index) => {
                    const inverse = row.label.includes('Discarded') || row.label.includes('Reconstructed')
                    const label = trustComparisonLabel(values, index, inverse)
                    return (
                      <div key={`${memo.netuidLabel}-${row.label}`} className="surface-subtle p-4">
                        <div className="flex items-center justify-between gap-3">
                          <div className="text-sm text-[color:var(--text-secondary)]">{memo.name}</div>
                          {label ? (
                            <span className={cn('rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.18em]', toneClass(inverse ? 'warning' : 'quality'))}>
                              {label}
                            </span>
                          ) : null}
                        </div>
                        <div className="mt-2 text-lg font-semibold text-[color:var(--text-primary)]">{row.values[index]?.value ?? 'n/a'}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      </section>

      <section className="surface-panel p-5 sm:p-6">
        {matrixSectionTitle('Upside vs Break Risk', 'Compare the main reasons a subnet can work against the specific ways the thesis can break.')}
        <div className={cn('grid gap-4', compareGridClass(memos.length))}>
          {memos.map((memo) => (
            <div key={memo.netuidLabel} className="surface-subtle p-4">
              <div className="mb-4 text-lg font-semibold tracking-tight text-[color:var(--text-primary)]">{memo.name}</div>
              <div className="grid gap-4">
                <InsightColumn title="Top drivers" items={memo.interesting} empty="No positive drivers surfaced." />
                <InsightColumn title="Top drags" items={memo.breaks} empty="No drags surfaced." />
                <InsightColumn title="Thesis breakers" items={memo.breaks.filter((item) => item.title === 'Thesis breaker')} empty="No explicit thesis breakers surfaced." />
                <InsightColumn title="Fragility contributors" items={memo.fragilityContributors} empty="No fragility contributors surfaced." />
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="surface-panel p-5 sm:p-6">
        {matrixSectionTitle('Stress and Execution', 'Stress drawdown, liquidity, market context, and operating fragility help determine whether the upside survives real-world conditions.')}
        <div className={cn('grid gap-4', compareGridClass(memos.length))}>
          {memos.map((memo) => (
            <div key={memo.netuidLabel} className="surface-subtle p-4">
              <div className="text-lg font-semibold tracking-tight text-[color:var(--text-primary)]">{memo.name}</div>
              <div className="mt-4 grid gap-3">
                {memo.stressItems.map((item, index) => (
                  <MetricCard key={`${item.title}-${index}`} label={item.title} value={item.body} meta={item.meta} accent={item.tone === 'neutral' ? 'default' : item.tone} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="surface-panel p-5 sm:p-6">
        {matrixSectionTitle('Links and Next Actions', 'Use the compare read to decide which memos deserve deeper attention or external corroboration.')}
        <div className={cn('grid gap-4', compareGridClass(memos.length))}>
          {memos.map((memo) => (
            <div key={memo.netuidLabel} className="surface-subtle p-4">
              <div className="text-lg font-semibold tracking-tight text-[color:var(--text-primary)]">{memo.name}</div>
              <div className="mt-4 flex flex-col gap-2">
                <Link href={memo.href} className="button-primary">
                  Open research memo
                </Link>
                {memo.links.map((link) => (
                  <a key={link.href} href={link.href} target="_blank" rel="noreferrer" className="button-secondary">
                    {link.label}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
