import Link from 'next/link'

import CollapsibleSection from '@/components/ui/CollapsibleSection'
import MetricCard from '@/components/ui/MetricCard'
import PageHeader from '@/components/ui/PageHeader'
import SignalBar from '@/components/ui/SignalBar'
import StatusChip from '@/components/ui/StatusChip'
import TrustBadge from '@/components/ui/TrustBadge'
import { DetailMemoViewModel, MemoSectionItem } from '@/lib/view-models/research'

function InsightList({ items, empty }: { items: MemoSectionItem[]; empty: string }) {
  if (!items.length) {
    return <div className="surface-subtle p-4 text-sm text-[color:var(--text-tertiary)]">{empty}</div>
  }

  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div key={`${item.title}-${index}`} className="surface-subtle p-4">
          <div className="text-sm font-medium text-[color:var(--text-primary)]">{item.title}</div>
          <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{item.body}</p>
          {item.meta ? <div className="mt-2 text-xs uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{item.meta}</div> : null}
        </div>
      ))}
    </div>
  )
}

export default function ResearchWorkspace({ memo }: { memo: DetailMemoViewModel }) {
  const trustWarning = memo.summaryFlags.length > 0

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
            <StatusChip tone={memo.modelLabelTone}>{memo.modelLabel}</StatusChip>
          </div>
        }
        stats={[
          { label: 'Rank', value: memo.rankLabel },
          { label: 'Percentile', value: memo.percentileLabel },
          { label: 'Updated', value: memo.updatedLabel, tone: trustWarning ? 'warning' : 'default' },
        ]}
      />

      <section className="surface-panel p-5 sm:p-6">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_340px]">
          <div className="space-y-5">
            <div className="surface-subtle p-4">
              <div className="eyebrow text-[color:var(--mispricing-strong)]">Decision framing</div>
              <p className="mt-2 text-base leading-7 text-[color:var(--text-secondary)]">{memo.decisionLine}</p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {memo.signals.map((signal) => (
                <SignalBar key={signal.key} signal={signal} />
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <div className="surface-subtle p-4">
              <div className="section-title text-base">Trust state</div>
              <div className="mt-3">
                <TrustBadge flags={memo.summaryFlags} awaitingRun={memo.awaitingRun} />
              </div>
            </div>

            {memo.summaryFlags.length ? (
              <div className="surface-subtle p-4 ring-1 ring-[color:var(--warning-border)]">
                <div className="eyebrow text-[color:var(--warning-strong)]">Trust alert</div>
                <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">
                  Telemetry repairs, discarded inputs, stale runs, or weak confidence can materially change the memo. Check the trust section before underwriting the thesis.
                </p>
              </div>
            ) : null}

            <div className="grid gap-3">
              {memo.summaryMetrics.map((item) => (
                <MetricCard key={item.label} label={item.label} value={item.value} meta={item.meta} accent={item.tone === 'neutral' || !item.tone ? 'default' : item.tone} />
              ))}
            </div>
          </div>
        </div>
      </section>

      <CollapsibleSection title="Why now" subtitle="The positive case: top drivers, signal contributors, and the block scores carrying the thesis.">
        <div className="space-y-6">
          <InsightList items={memo.interesting} empty="No positive drivers were emitted." />
          {memo.signalContributorSections.length ? (
            <div className="grid gap-4 xl:grid-cols-2">
              {memo.signalContributorSections.map((section) => (
                <div key={section.title} className="space-y-3">
                  <div className="section-title text-base">{section.title}</div>
                  <InsightList items={section.items} empty={`No ${section.title.toLowerCase()} surfaced.`} />
                </div>
              ))}
            </div>
          ) : null}
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {memo.blockScores.map((item, index) => (
              <MetricCard key={`${item.title}-${index}`} label={item.title} value={item.body} meta={item.meta} accent={item.tone === 'neutral' || !item.tone ? 'default' : item.tone} />
            ))}
          </div>
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="What breaks" subtitle="Negative drags, thesis breakers, and fragility contributors that can invalidate the setup.">
        <div className="grid gap-6 xl:grid-cols-2">
          <div className="space-y-3">
            <div className="section-title text-base">Negative drags and breakers</div>
            <InsightList items={memo.breaks} empty="No explicit failure modes were emitted." />
          </div>
          <div className="space-y-3">
            <div className="section-title text-base">Fragility contributors</div>
            <InsightList items={memo.fragilityContributors} empty="No fragility contributors surfaced." />
          </div>
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Can I trust this" subtitle="Confidence, reliability, telemetry visibility, and the uncertainties still able to move the memo.">
        <div className="space-y-6">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {memo.confidenceHeadline.map((item) => (
              <MetricCard key={item.label} label={item.label} value={item.value} meta={item.meta} accent={item.tone === 'neutral' || !item.tone ? 'default' : item.tone} />
            ))}
          </div>
          <div className="grid gap-6 xl:grid-cols-2">
            <div className="space-y-3">
              <div className="section-title text-base">Reliability</div>
              <InsightList items={memo.confidenceItems} empty="No reliability data was emitted." />
            </div>
            <div className="space-y-3">
              <div className="section-title text-base">Key uncertainties</div>
              <InsightList items={memo.uncertainties} empty="No key uncertainties were emitted." />
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {memo.visibilityItems.map((item, index) => (
              <MetricCard key={`${item.title}-${index}`} label={item.title} value={item.body} meta={item.meta} accent={item.tone === 'neutral' || !item.tone ? 'default' : item.tone} />
            ))}
          </div>
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Stress and execution" subtitle="Fragility class, drawdown behavior, scenarios, and market structure once the thesis meets real conditions.">
        <div className="space-y-6">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {memo.stressItems.map((item, index) => (
              <MetricCard key={`${item.title}-${index}`} label={item.title} value={item.body} meta={item.meta} accent={item.tone === 'neutral' || !item.tone ? 'default' : item.tone} />
            ))}
          </div>
          <div className="space-y-3">
            <div className="section-title text-base">Stress scenarios</div>
            <InsightList items={memo.scenarioItems} empty="No stress scenarios were provided." />
          </div>
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Raw context" subtitle="Supporting market context and external links stay available, but collapsed behind the thesis, trust, and stress sections." defaultOpen={false}>
        <div className="space-y-6">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {memo.rawContext.map((item, index) => (
              <MetricCard key={`${item.title}-${index}`} label={item.title} value={item.body} meta={item.meta} accent={item.tone === 'neutral' || !item.tone ? 'default' : item.tone} />
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {memo.links.map((link) => (
              <a key={link.href} href={link.href} target="_blank" rel="noreferrer" className="button-secondary">
                {link.label}
              </a>
            ))}
          </div>
        </div>
      </CollapsibleSection>
    </div>
  )
}
