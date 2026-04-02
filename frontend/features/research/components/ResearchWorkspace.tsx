import Link from 'next/link'

import PageHeader from '@/components/ui/PageHeader'
import SignalBar from '@/components/ui/SignalBar'
import StatusChip from '@/components/ui/StatusChip'
import { DetailMemoViewModel, MemoSectionItem } from '@/lib/view-models/research'

function pickMetric(
  memo: DetailMemoViewModel,
  label: string,
): { label: string; value: string; tone?: string; meta?: string } | null {
  return memo.summaryMetrics.find((item) => item.label === label) ?? null
}

function toHeaderTone(tone: string | undefined): 'default' | 'warning' | 'success' {
  if (tone === 'warning' || tone === 'fragility') return 'warning'
  if (tone === 'quality' || tone === 'confidence') return 'success'
  return 'default'
}

function sentenceParts(items: MemoSectionItem[], limit = 2): string[] {
  return items
    .slice(0, limit)
    .map((item) => item.body.trim())
    .filter(Boolean)
}

function signalNumber(memo: DetailMemoViewModel, key: string): string {
  const signal = memo.signals.find((item) => item.key === key)
  return signal?.value == null ? 'n/a' : signal.value.toFixed(1)
}

function buildInvestmentRead(memo: DetailMemoViewModel): string {
  const positive = sentenceParts(memo.interesting, 1)[0]
  const risk = sentenceParts(memo.breaks, 1)[0]
  const uncertainty = sentenceParts(memo.uncertainties, 1)[0]

  const parts = [memo.decisionLine]
  if (positive) parts.push(`What supports that read today: ${positive}`)
  if (risk) parts.push(`What still needs to be respected: ${risk}`)
  if (uncertainty) parts.push(`What can still move the memo: ${uncertainty}`)
  return parts.join(' ')
}

function cleanText(value: string): string {
  return value.replace(/\s+/g, ' ').trim()
}

function buildMetricNarrative({
  scoreLabel,
  scoreValue,
  opening,
  positives,
  limiter,
  closer,
}: {
  scoreLabel: string
  scoreValue: string
  opening: string
  positives: string[]
  limiter?: string
  closer?: string
}): string {
  const parts = [`${scoreLabel} is ${scoreValue} ${opening}`]
  if (positives[0]) parts.push(positives[0])
  if (positives[1]) parts.push(positives[1])
  if (limiter) parts.push(limiter)
  if (closer) parts.push(closer)
  return parts.join(' ')
}

function NarrativeSection({
  title,
  body,
}: {
  title: string
  body: string
}) {
  return (
    <div className="surface-subtle p-4">
      <div className="eyebrow">{title}</div>
      <p className="mt-2 text-sm leading-7 text-[color:var(--text-secondary)]">{body}</p>
    </div>
  )
}

export default function ResearchWorkspace({ memo }: { memo: DetailMemoViewModel }) {
  const rankMetric = pickMetric(memo, 'Rank')
  const updatedMetric = pickMetric(memo, 'Updated')
  const confidenceMetric = memo.confidenceHeadline.find((item) => item.label === 'Signal confidence') ?? null

  const strengthItems =
    memo.signalContributorSections.find((section) => section.title === 'Quality contributors')?.items ??
    memo.interesting
  const upsideItems =
    memo.signalContributorSections.find((section) => section.title === 'Mispricing contributors')?.items ??
    memo.interesting
  const riskItems = memo.fragilityContributors.length ? memo.fragilityContributors : memo.breaks
  const evidenceItems = memo.uncertainties.length ? memo.uncertainties : memo.confidenceItems
  const stressDrawdown = memo.stressItems.find((item) => item.title === 'Stress drawdown')?.body
  const fragilityClass = memo.stressItems.find((item) => item.title === 'Fragility class')?.body

  const strengthNarrative = buildMetricNarrative({
    scoreLabel: 'Strength',
    scoreValue: signalNumber(memo, 'fundamental_quality'),
    opening: 'because the subnet is showing real operating quality rather than just price momentum.',
    positives: strengthItems.slice(0, 2).map((item) => cleanText(item.body)),
    limiter: memo.breaks[0] ? `It is not materially higher because ${cleanText(memo.breaks[0].body).toLowerCase()}` : undefined,
    closer: Number(signalNumber(memo, 'fundamental_quality')) >= 70
      ? 'That leaves the subnet looking fundamentally strong, even if not flawless.'
      : 'That leaves the subnet looking solid, but not dominant.'
  })

  const upsideNarrative = buildMetricNarrative({
    scoreLabel: 'Upside Gap',
    scoreValue: signalNumber(memo, 'mispricing_signal'),
    opening: 'because the model sees some mismatch between current pricing and the underlying setup, but not a major dislocation.',
    positives: upsideItems.slice(0, 2).map((item) => cleanText(item.body)),
    limiter: memo.breaks[0] ? `The score stays capped because ${cleanText(memo.breaks[0].body).toLowerCase()}` : undefined,
    closer: Number(signalNumber(memo, 'mispricing_signal')) >= 50
      ? 'In other words, there is still a real upside case here.'
      : 'In other words, the opportunity looks real but not obviously mispriced.'
  })

  const riskNarrative = buildMetricNarrative({
    scoreLabel: 'Risk',
    scoreValue: signalNumber(memo, 'fragility_risk'),
    opening: 'because the subnet still looks relatively resilient under stress rather than obviously fragile.',
    positives: riskItems.slice(0, 2).map((item) => cleanText(item.body)),
    limiter: stressDrawdown ? `The modeled stress drawdown still reaches ${stressDrawdown.toLowerCase()}, so this is not risk-free.` : undefined,
    closer: fragilityClass ? `Overall, the model currently classifies the setup as ${fragilityClass.toLowerCase()}.` : undefined,
  })

  const evidenceNarrative = buildMetricNarrative({
    scoreLabel: 'Evidence Quality',
    scoreValue: signalNumber(memo, 'signal_confidence'),
    opening: 'because the read is usable, but not fully clean.',
    positives: evidenceItems.slice(0, 2).map((item) => cleanText(item.body)),
    limiter: memo.uncertainties[0] ? `The biggest reason for caution is that ${cleanText(memo.uncertainties[0].body).toLowerCase()}` : undefined,
    closer: 'So the memo is actionable, but it still deserves some skepticism rather than full conviction.',
  })

  return (
    <div className="space-y-6 pb-12">
      <Link href="/" className="button-secondary">
        Back to discover
      </Link>

      <PageHeader
        title={memo.name}
        subtitle={memo.thesis}
        variant="research"
        actions={
          <div className="flex flex-wrap gap-2">
            <StatusChip tone="neutral">{memo.netuidLabel}</StatusChip>
            {rankMetric ? <StatusChip tone="neutral">{rankMetric.value}</StatusChip> : null}
          </div>
        }
        stats={[
          ...(updatedMetric ? [{ label: 'Updated', value: updatedMetric.value }] : []),
          ...(confidenceMetric ? [{ label: 'Evidence quality', value: confidenceMetric.value, tone: toHeaderTone(confidenceMetric.tone) }] : []),
        ]}
      />

      <section className="surface-panel p-5 sm:p-6">
        <div className="space-y-5">
          <div className="surface-subtle p-4">
            <div className="eyebrow text-[color:var(--mispricing-strong)]">Investment read</div>
            <p className="mt-2 text-base leading-7 text-[color:var(--text-secondary)]">{buildInvestmentRead(memo)}</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {memo.signals.map((signal) => (
              <SignalBar key={signal.key} signal={signal} />
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <NarrativeSection
              title="Why Strength Looks Like This"
              body={strengthNarrative}
            />
            <NarrativeSection
              title="Why Upside Gap Looks Like This"
              body={upsideNarrative}
            />
            <NarrativeSection
              title="Why Risk Looks Like This"
              body={riskNarrative}
            />
            <NarrativeSection
              title="Why Evidence Quality Looks Like This"
              body={evidenceNarrative}
            />
          </div>
        </div>
      </section>
    </div>
  )
}
