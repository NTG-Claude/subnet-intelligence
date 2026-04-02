import Link from 'next/link'

import MetricCard from '@/components/ui/MetricCard'
import PageHeader from '@/components/ui/PageHeader'
import SignalBar from '@/components/ui/SignalBar'
import StatusChip from '@/components/ui/StatusChip'
import { DetailMemoViewModel, MemoSectionItem } from '@/lib/view-models/research'

function CompactInsightList({
  items,
  empty,
  limit = 3,
}: {
  items: MemoSectionItem[]
  empty: string
  limit?: number
}) {
  const visible = items.slice(0, limit)

  if (!visible.length) {
    return <div className="surface-subtle p-4 text-sm text-[color:var(--text-tertiary)]">{empty}</div>
  }

  return (
    <div className="space-y-3">
      {visible.map((item, index) => (
        <div key={`${item.title}-${index}`} className="surface-subtle p-4">
          <div className="text-sm font-medium text-[color:var(--text-primary)]">{item.title}</div>
          <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{item.body}</p>
        </div>
      ))}
    </div>
  )
}

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

export default function ResearchWorkspace({ memo }: { memo: DetailMemoViewModel }) {
  const rankMetric = pickMetric(memo, 'Rank')
  const updatedMetric = pickMetric(memo, 'Updated')
  const confidenceMetric = memo.confidenceHeadline.find((item) => item.label === 'Signal confidence') ?? null
  const dataMetric = memo.confidenceHeadline.find((item) => item.label === 'Data confidence') ?? null
  const thesisMetric = memo.confidenceHeadline.find((item) => item.label === 'Thesis confidence') ?? null

  const topStressItems = memo.stressItems.filter((item) =>
    ['Fragility class', 'Stress drawdown', 'Market cap', 'Pool depth'].includes(item.title),
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
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_320px]">
          <div className="space-y-5">
            <div className="surface-subtle p-4">
              <div className="eyebrow text-[color:var(--mispricing-strong)]">Investment read</div>
              <p className="mt-2 text-base leading-7 text-[color:var(--text-secondary)]">{memo.decisionLine}</p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {memo.signals.map((signal) => (
                <SignalBar key={signal.key} signal={signal} />
              ))}
            </div>
          </div>

          <div className="grid gap-3">
            {dataMetric ? (
              <MetricCard label="Data confidence" value={dataMetric.value} accent={dataMetric.tone === 'neutral' || !dataMetric.tone ? 'default' : dataMetric.tone} />
            ) : null}
            {thesisMetric ? (
              <MetricCard label="Thesis confidence" value={thesisMetric.value} accent={thesisMetric.tone === 'neutral' || !thesisMetric.tone ? 'default' : thesisMetric.tone} />
            ) : null}
            {topStressItems.slice(0, 2).map((item, index) => (
              <MetricCard
                key={`${item.title}-${index}`}
                label={item.title}
                value={item.body}
                meta={item.meta}
                accent={item.tone === 'neutral' || !item.tone ? 'default' : item.tone}
              />
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-3">
          <div className="section-title">Why it can work</div>
          <p className="text-sm leading-6 text-[color:var(--text-secondary)]">
            The strongest reasons this subnet currently earns a place near the top of the list.
          </p>
          <CompactInsightList items={memo.interesting} empty="No clear positive drivers were emitted." />
        </div>

        <div className="space-y-3">
          <div className="section-title">What could break it</div>
          <p className="text-sm leading-6 text-[color:var(--text-secondary)]">
            The main failure modes and drags that can invalidate the upside case.
          </p>
          <CompactInsightList items={memo.breaks} empty="No explicit failure modes were emitted." />
        </div>

        <div className="space-y-3">
          <div className="section-title">How much to trust it</div>
          <p className="text-sm leading-6 text-[color:var(--text-secondary)]">
            The most important uncertainties still able to move the memo.
          </p>
          <CompactInsightList items={memo.uncertainties} empty="No major trust warnings were emitted." />
        </div>
      </section>

      <section className="surface-panel p-5 sm:p-6">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
          <div className="space-y-3">
            <div className="section-title">Stress view</div>
            <p className="text-sm leading-6 text-[color:var(--text-secondary)]">
              A compact view of how the thesis behaves once it meets real conditions and adverse scenarios.
            </p>
            <CompactInsightList items={memo.scenarioItems} empty="No stress scenarios were provided." limit={3} />
          </div>

          <div className="space-y-3">
            <div className="section-title">Links</div>
            <div className="flex flex-wrap gap-2">
              {memo.links.map((link) => (
                <a key={link.href} href={link.href} target="_blank" rel="noreferrer" className="button-secondary">
                  {link.label}
                </a>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
