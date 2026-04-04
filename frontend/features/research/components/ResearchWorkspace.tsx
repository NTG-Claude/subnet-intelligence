import Link from 'next/link'

import CollapsibleSection from '@/components/ui/CollapsibleSection'
import SignalBar from '@/components/ui/SignalBar'
import StatusChip from '@/components/ui/StatusChip'
import { SubnetSignalHistoryPoint } from '@/lib/api'
import { DetailMemoViewModel, MemoInsightItem, MemoSectionItem, ScoreExplanationItem, SignalStat } from '@/lib/view-models/research'
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

function ThesisPanel({
  tone,
  title,
  summary,
  items,
}: {
  tone: 'bull' | 'bear'
  title: string
  summary: string
  items: Array<{ title: string; body: string }>
}) {
  const shellClass =
    tone === 'bull'
      ? 'border-[color:rgba(74,222,128,0.12)] bg-[linear-gradient(180deg,rgba(18,32,24,0.32),rgba(10,18,26,0.92))]'
      : 'border-[color:rgba(244,114,182,0.12)] bg-[linear-gradient(180deg,rgba(38,20,28,0.32),rgba(10,18,26,0.92))]'
  const labelClass = tone === 'bull' ? 'text-[color:rgba(134,239,172,0.9)]' : 'text-[color:rgba(251,182,206,0.9)]'
  const rowClass =
    tone === 'bull'
      ? 'border-[color:rgba(74,222,128,0.1)]'
      : 'border-[color:rgba(244,114,182,0.1)]'

  return (
    <div className={`rounded-[var(--radius-xl)] border p-5 sm:p-6 ${shellClass}`}>
      <div className={`eyebrow ${labelClass}`}>{title}</div>
      <p className="mt-2 min-h-[72px] text-sm leading-6 text-[color:var(--text-primary)]">{summary}</p>
      {items.length ? (
        <div className="mt-4 divide-y divide-[color:var(--border-subtle)]">
          {items.map((item, index) => (
            <div key={`${title}-${item.title}-${index}`} className={`py-3 first:pt-0 last:pb-0 ${rowClass}`}>
              <div className="text-sm font-medium text-[color:var(--text-primary)]">{item.title}</div>
              <p className="mt-1.5 text-sm leading-6 text-[color:var(--text-secondary)]">{item.body}</p>
            </div>
          ))}
        </div>
      ) : null}
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
        <DiagnosticGrid items={items} empty={empty} showMeta={false} />
      </div>
    </section>
  )
}

function cleanVisibleText(text: string | undefined | null): string {
  const value = (text ?? '').trim()
  if (!value) return ''

  return value
    .replace(/\bEvidence penalty\.\s*/gi, '')
    .replace(/\bConfidence drag\.\s*/gi, '')
    .replace(/\bValuation gap\.\s*/gi, '')
    .replace(/\bInput quality\.\s*/gi, '')
    .replace(/\bThesis coherence\.\s*/gi, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function uniqueSectionItems(items: MemoSectionItem[]): MemoSectionItem[] {
  const seen = new Set<string>()

  return items.filter((item) => {
    const key = `${cleanVisibleText(item.title).toLowerCase()}::${cleanVisibleText(item.body).toLowerCase()}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function semanticKey(title: string, body: string): string {
  const text = `${cleanVisibleText(title)} ${cleanVisibleText(body)}`.toLowerCase()
  if (/(confidence|reliable|trust|evidence|telemetry|history|dropped|rebuilt|discarded|reconstructed)/.test(text)) {
    return 'trust'
  }
  if (/(stress|drawdown|downside|fragility|break)/.test(text)) {
    return 'stress'
  }
  if (/(usage|activity|quality|health|dev|efficiency)/.test(text)) {
    return 'quality'
  }
  if (/(price|market|upside|opportunity|valuation)/.test(text)) {
    return 'market'
  }
  return text
}

function dedupeComparisonSupports(items: ScoreExplanationItem[]): ScoreExplanationItem[] {
  const seen = new Set<string>()
  const result: ScoreExplanationItem[] = []

  for (const item of items) {
    const key = semanticKey(item.title, item.body)
    if (seen.has(key)) continue
    seen.add(key)
    result.push(item)
    if (result.length >= 2) break
  }

  return result
}

function dedupeComparisonRisks(items: MemoSectionItem[]): MemoSectionItem[] {
  const seen = new Set<string>()
  const result: MemoSectionItem[] = []

  for (const item of items) {
    const key = semanticKey(item.title, item.body)
    if (seen.has(key)) continue
    seen.add(key)
    result.push(item)
    if (result.length >= 3) break
  }

  return result
}

function signalValue(signals: SignalStat[], label: string): number | null {
  return signals.find((signal) => signal.label === label)?.value ?? null
}

function formatSignalValue(value: number | null): string {
  return value == null ? 'n/a' : value.toFixed(1)
}

function formatWhole(value: number | null | undefined): string {
  return value == null ? 'n/a' : value.toFixed(0)
}

function isLowUpside(memo: DetailMemoViewModel): boolean {
  const opportunity = signalValue(memo.signals, 'Opportunity')
  return opportunity != null && opportunity < 45
}

function thesisBarometer(memo: DetailMemoViewModel): {
  label: string
  value: number
  toneClass: string
  trackClass: string
} {
  const quality = signalValue(memo.signals, 'Quality') ?? 50
  const opportunity = signalValue(memo.signals, 'Opportunity') ?? 50
  const confidence = signalValue(memo.signals, 'Confidence') ?? 50
  const risk = signalValue(memo.signals, 'Risk')
  const safety = risk == null ? 50 : 100 - risk

  const composite = quality * 0.32 + opportunity * 0.24 + confidence * 0.2 + safety * 0.24

  if (composite >= 72) {
    return {
      label: 'Strongly bullish',
      value: composite,
      toneClass: 'bg-[color:rgba(74,222,128,0.95)]',
      trackClass: 'bg-[linear-gradient(90deg,rgba(74,222,128,0.22),rgba(74,222,128,0.05))]',
    }
  }
  if (composite >= 60) {
    return {
      label: 'Bullish',
      value: composite,
      toneClass: 'bg-[color:rgba(134,239,172,0.9)]',
      trackClass: 'bg-[linear-gradient(90deg,rgba(134,239,172,0.2),rgba(134,239,172,0.05))]',
    }
  }
  if (composite >= 48) {
    return {
      label: 'Balanced',
      value: composite,
      toneClass: 'bg-[color:rgba(250,204,21,0.9)]',
      trackClass: 'bg-[linear-gradient(90deg,rgba(250,204,21,0.2),rgba(250,204,21,0.05))]',
    }
  }
  if (composite >= 36) {
    return {
      label: 'Bearish',
      value: composite,
      toneClass: 'bg-[color:rgba(251,146,60,0.9)]',
      trackClass: 'bg-[linear-gradient(90deg,rgba(251,146,60,0.2),rgba(251,146,60,0.05))]',
    }
  }
  return {
    label: 'Strongly bearish',
    value: composite,
    toneClass: 'bg-[color:rgba(244,114,182,0.95)]',
    trackClass: 'bg-[linear-gradient(90deg,rgba(244,114,182,0.2),rgba(244,114,182,0.05))]',
  }
}

function countFromItem(items: MemoSectionItem[], title: string): number {
  const raw = items.find((item) => item.title === title)?.body
  const parsed = raw ? Number(raw) : NaN
  return Number.isFinite(parsed) ? parsed : 0
}

function buildHeroVerdict(memo: DetailMemoViewModel): string {
  const quality = signalValue(memo.signals, 'Quality')
  const opportunity = signalValue(memo.signals, 'Opportunity')
  const risk = signalValue(memo.signals, 'Risk')
  const confidence = signalValue(memo.signals, 'Confidence')
  const breakdown = memo.scoreBreakdown
  const lowUpside = isLowUpside(memo)

  if ([quality, opportunity, risk, confidence].every((value) => value == null)) {
    return 'This subnet is still waiting on a clean run, so the rank is provisional.'
  }

  const positives: string[] = []
  const limits: string[] = []

  if (quality != null) {
    if (quality >= 65 && breakdown) {
      const reasons = [
        breakdown.activity != null && breakdown.activity >= 60 ? `activity (${formatWhole(breakdown.activity)})` : '',
        breakdown.health != null && breakdown.health >= 60 ? `health (${formatWhole(breakdown.health)})` : '',
        breakdown.dev != null && breakdown.dev >= 60 ? `dev activity (${formatWhole(breakdown.dev)})` : '',
        breakdown.efficiency != null && breakdown.efficiency >= 60 ? `efficiency (${formatWhole(breakdown.efficiency)})` : '',
      ].filter(Boolean)
      if (reasons.length) positives.push(`The rank gets support from real operating quality: ${reasons.join(', ')} are all holding up.`)
    } else if (quality < 55) {
      limits.push(`Quality is weak enough that the subnet is not doing enough on fundamentals to earn a higher rank.`)
    }
  }

  if (opportunity != null) {
    if (quality != null && quality >= 60 && lowUpside) {
      positives.push(`The subnet still ranks well because the operating side is solid even though the easy upside may already be gone.`)
      limits.push(`It is not higher because the market is no longer leaving a large pricing gap.`)
    } else if (opportunity >= 60) {
      positives.push(`Price still looks behind the operating picture, so there is a real upside case on top of the current quality.`)
    }
  }

  if (risk != null) {
    if (risk <= 25 && memo.stressDrawdown != null) {
      positives.push(`Modeled drawdown is only ${memo.stressDrawdown.toFixed(1)}%, so downside is relatively contained for now.`)
    } else if (risk >= 60) {
      limits.push(`Modeled downside is still severe enough that the case can break quickly if conditions worsen.`)
    }
  }

  if (confidence != null && confidence < 60) {
    const dataGaps = [
      memo.droppedInputs ? `${memo.droppedInputs} dropped inputs` : '',
      memo.rebuiltInputs ? `${memo.rebuiltInputs} rebuilt inputs` : '',
    ].filter(Boolean)
    limits.push(
      dataGaps.length
        ? `Confidence is still capped by data gaps: ${dataGaps.join(' and ')}.`
        : `Confidence is still not clean enough to fully trust the rank.`,
    )
  }

  return [...positives.slice(0, 2), ...limits.slice(0, 2)].join(' ')
}

function buildPositiveDriverText(memo: DetailMemoViewModel): string {
  const breakdown = memo.scoreBreakdown
  const quality = signalValue(memo.signals, 'Quality')
  const opportunity = signalValue(memo.signals, 'Opportunity')
  const lowUpside = isLowUpside(memo)

  if (breakdown && quality != null && quality >= 60) {
    const reasons = [
      breakdown.activity != null && breakdown.activity >= 60 ? `activity is strong (${formatWhole(breakdown.activity)})` : '',
      breakdown.health != null && breakdown.health >= 60 ? `health is solid (${formatWhole(breakdown.health)})` : '',
      breakdown.dev != null && breakdown.dev >= 60 ? `dev activity is active (${formatWhole(breakdown.dev)})` : '',
      breakdown.efficiency != null && breakdown.efficiency >= 60 ? `efficiency is good (${formatWhole(breakdown.efficiency)})` : '',
    ].filter(Boolean)

    if (reasons.length) {
      return `The quality case is real because ${reasons.join(', ')}.`
    }
  }

  if (!lowUpside && opportunity != null && quality != null && quality > opportunity + 10) {
    return `Quality is reading better than price, which suggests the market has not fully caught up to the operating picture.`
  }

  if (memo.stressDrawdown != null) {
    return `Modeled drawdown is only ${memo.stressDrawdown.toFixed(1)}%, so downside is not the main thing hurting this subnet right now.`
  }

  return 'No single positive driver stands out yet.'
}

function buildLimitingFactorText(memo: DetailMemoViewModel): string {
  const quality = signalValue(memo.signals, 'Quality')
  const opportunity = signalValue(memo.signals, 'Opportunity')
  const confidence = signalValue(memo.signals, 'Confidence')
  const dropped = countFromItem(memo.visibilityItems, 'Dropped inputs')
  const rebuilt = countFromItem(memo.visibilityItems, 'Rebuilt inputs')
  const breakdown = memo.scoreBreakdown

  if (confidence != null && (dropped > 0 || rebuilt > 0)) {
    const parts = [rebuilt ? `${rebuilt} rebuilt inputs` : '', dropped ? `${dropped} dropped inputs` : ''].filter(Boolean)
    return `The read is still hard to trust because it relies on ${parts.join(' and ')}. That keeps the score cautious even if some headline signals look good.`
  }

  if (opportunity != null && opportunity < 45 && quality != null && quality >= 60) {
    return `The subnet may be solid, but it is not ranked higher because the market is not obviously underpricing it anymore.`
  }

  if (breakdown?.capital != null && breakdown.capital < 50) {
    return `Capital support is weak (${formatWhole(breakdown.capital)}), so the market side of the case is not as strong as the operating side.`
  }

  if (quality != null && quality < 55) {
    return `Quality is not high enough yet to justify a much better rank.`
  }

  return 'No single limiting factor stands out yet.'
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
  const verdict = buildHeroVerdict(memo)
  const strongestSupport = buildPositiveDriverText(memo)
  const mainLimiter = buildLimitingFactorText(memo)
  const trustSummary = memo.evidenceItems[0]?.body ?? 'Trust details are not available yet.'
  const barometer = thesisBarometer(memo)

  const riskItems = uniqueSectionItems([
    ...memo.topDrags.map((item) => ({ title: item.title, body: item.body, tone: item.tone })),
    ...memo.breaks.filter((item) => item.title === 'Thesis breaker'),
    ...memo.uncertainties,
  ]).map((item) => ({
    ...item,
    title: cleanVisibleText(item.title),
    body: cleanVisibleText(item.body),
    meta: undefined,
  }))
  const primarySupports = dedupeComparisonSupports(memo.topSupports)
  const extraSupports = memo.topSupports.slice(2)
  const primaryRisks = dedupeComparisonRisks(riskItems)
  const extraRisks = riskItems.slice(4)
  const lowUpside = isLowUpside(memo)

  const heroSupports = primarySupports.filter((item) => !(lowUpside && semanticKey(item.title, item.body) === 'market')).slice(0, 2)
  const heroRisks = primaryRisks.slice(0, 2)

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
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_320px]">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip tone="neutral">{memo.netuidLabel}</StatusChip>
            </div>
            <h1 className="mt-4 text-3xl font-semibold tracking-tight text-[color:var(--text-primary)] sm:text-4xl">{memo.name}</h1>
            <div className="mt-2 text-sm text-[color:var(--text-tertiary)]">Updated {memo.updatedLabel}</div>

            <div className="mt-5 max-w-[420px] rounded-[var(--radius-lg)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-2)] p-3.5">
              <div className="flex items-center justify-between gap-3">
                <div className="eyebrow">Overall setup</div>
                <div className="text-sm font-medium text-[color:var(--text-primary)]">{barometer.label}</div>
              </div>
              <div className={`mt-3 h-2 rounded-full ${barometer.trackClass}`}>
                <div
                  className={`h-2 rounded-full ${barometer.toneClass}`}
                  style={{ width: `${Math.max(8, Math.min(100, barometer.value))}%` }}
                />
              </div>
            </div>

            <p className="mt-5 max-w-3xl text-[15px] leading-8 text-[color:var(--text-primary)]">{verdict}</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1 xl:content-start">
            <CompactStat label="Score" value={memo.scoreLabel} />
            <CompactStat label="Rank" value={memo.rankLabel} />
          </div>
        </div>

        <div className="mt-6 grid gap-4 xl:grid-cols-2">
          <ThesisPanel
            tone="bull"
            title="Bullish case"
            summary={strongestSupport}
            items={heroSupports.map((item) => ({ title: item.title, body: item.body }))}
          />
          <ThesisPanel
            tone="bear"
            title="Bearish case"
            summary={mainLimiter}
            items={heroRisks.map((item) => ({ title: item.title, body: item.body }))}
          />
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
        <PrimarySignalsTrend netuid={netuid} initialPoints={initialSignalHistory} />
      </section>

      <CollapsibleSection
        title="Deep Diagnostics"
        subtitle="Trust detail, market structure, and lower-level stress or scoring checks."
        defaultOpen={false}
      >
        <div className="space-y-6">
          <div>
            <div className="section-title">Trust & Evidence</div>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)]">{trustSummary}</p>
            <div className="mt-3">
              <DiagnosticGrid items={trustItems} empty="No trust details are available yet." />
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

          {extraSupports.length ? (
            <div>
              <div className="section-title">Additional Support</div>
              <div className="mt-3">
                <DiagnosticGrid
                  items={extraSupports.map((item) => ({ title: item.title, body: item.body, tone: item.tone }))}
                  empty="No additional support details are available."
                />
              </div>
            </div>
          ) : null}

          {extraRisks.length ? (
            <div>
              <div className="section-title">Additional Risks</div>
              <div className="mt-3">
                <DiagnosticGrid items={extraRisks} empty="No additional risk details are available." />
              </div>
            </div>
          ) : null}

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
