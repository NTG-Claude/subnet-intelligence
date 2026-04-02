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

function buildNarrative(
  lead: string,
  items: MemoSectionItem[],
  fallback: string,
): string {
  const points = items
    .slice(0, 3)
    .map((item) => cleanText(item.body))
    .filter(Boolean)

  if (!points.length) return fallback

  const [first, second, third] = points
  const sentences = [lead, first]
  if (second) sentences.push(second)
  if (third) sentences.push(third)
  return sentences.join(' ')
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

  const strengthNarrative = buildNarrative(
    'This score is mainly a read on how durable and fundamentally sound the subnet looks today.',
    strengthItems,
    'This score suggests the subnet looks fundamentally solid, but the current data does not surface many specific strengths.',
  )
  const upsideNarrative = buildNarrative(
    'This score reflects how much upside the model still sees from the current setup rather than how good the subnet is in absolute terms.',
    upsideItems,
    'This score suggests there may be some upside, but the current data does not point to a large valuation gap.',
  )
  const riskNarrative = buildNarrative(
    'This score is about how easily the thesis could break if conditions worsen, liquidity tightens, or execution disappoints.',
    riskItems,
    'This score suggests the model does not currently see one dominant break-risk factor.',
  )
  const evidenceNarrative = buildNarrative(
    'This score tells you how much trust to place in the read based on how clean, complete, and decision-useful the evidence is.',
    evidenceItems,
    'This score suggests the evidence base is reasonably usable, with no single warning dominating the memo.',
  )

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
