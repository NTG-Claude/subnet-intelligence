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

function DetailCluster({
  title,
  intro,
  items,
  empty,
}: {
  title: string
  intro: string
  items: MemoSectionItem[]
  empty: string
}) {
  return (
    <div className="surface-subtle p-4">
      <div className="eyebrow">{title}</div>
      <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{intro}</p>
      {items.length ? (
        <div className="mt-4 space-y-3">
          {items.slice(0, 3).map((item, index) => (
            <div key={`${item.title}-${index}`} className="rounded-[var(--radius-md)] border border-[color:var(--border-subtle)] bg-[color:var(--surface-3)] p-3">
              <div className="text-sm font-medium text-[color:var(--text-primary)]">{item.title}</div>
              <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{item.body}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-4 text-sm text-[color:var(--text-tertiary)]">{empty}</div>
      )}
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
            <DetailCluster
              title="Why Strength Looks Like This"
              intro="The strength score reflects the operating quality and durability the model sees in the subnet today."
              items={strengthItems}
              empty="No additional strength drivers were emitted."
            />
            <DetailCluster
              title="Why Upside Gap Looks Like This"
              intro="This explains why the model still sees, or does not see, enough valuation gap to justify upside from here."
              items={upsideItems}
              empty="No specific upside-gap drivers were emitted."
            />
            <DetailCluster
              title="Why Risk Looks Like This"
              intro="This captures the main ways the thesis can break under stress, crowding, liquidity pressure, or weaker execution."
              items={riskItems}
              empty="No specific risk drivers were emitted."
            />
            <DetailCluster
              title="Why Evidence Quality Looks Like This"
              intro="This explains how clean, complete, and decision-useful the underlying evidence base currently is."
              items={evidenceItems}
              empty="No specific evidence-quality warnings were emitted."
            />
          </div>
        </div>
      </section>
    </div>
  )
}
