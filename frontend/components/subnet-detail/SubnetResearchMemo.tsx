import Link from 'next/link'

import { DetailMemoViewModel } from '@/lib/view-models/research'
import { MemoList, MetricGrid, ResearchPanel, SignalPill, StatusBadge } from '@/components/shared/research-ui'

export default function SubnetResearchMemo({ memo }: { memo: DetailMemoViewModel }) {
  return (
    <div className="space-y-6">
      <Link href="/" className="inline-flex items-center text-sm text-stone-400 transition-colors hover:text-stone-100">
        Back to universe
      </Link>

      <section className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-6 sm:p-8">
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone="neutral">{memo.netuidLabel}</StatusBadge>
            <StatusBadge tone={memo.awaitingRun ? 'warning' : 'neutral'}>{memo.label}</StatusBadge>
          </div>

          <div className="space-y-3">
            <div className="flex flex-wrap items-end gap-4">
              <h1 className="text-3xl font-semibold tracking-tight text-stone-50 sm:text-4xl">{memo.name}</h1>
              <div className="text-sm text-stone-500">Updated {memo.updatedLabel}</div>
            </div>
            <p className="max-w-4xl text-base leading-7 text-stone-300">{memo.thesis}</p>
            <div className="text-sm leading-6 text-stone-400">{memo.decisionLine}</div>
          </div>

          <MetricGrid
            items={[
              { label: 'Rank', value: memo.rankLabel },
              { label: 'Percentile', value: memo.percentileLabel },
              { label: 'Updated', value: memo.updatedLabel },
              { label: 'Read state', value: memo.awaitingRun ? 'Awaiting fresh V2 output' : 'V2 research memo live' },
            ]}
          />

          <div className="grid gap-3 lg:grid-cols-4">
            {memo.signals.map((signal) => (
              <SignalPill key={signal.key} signal={signal} />
            ))}
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <ResearchPanel
          title="Why This Is Interesting"
          subtitle="Positive drivers, quality and mispricing contributors, and the core blocks that support the thesis."
        >
          <div className="space-y-5">
            <MemoList items={memo.interesting} empty="No positive V2 drivers were surfaced for this subnet." />
            <div className="grid gap-5 lg:grid-cols-2">
              <div>
                <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Quality contributors</div>
                <MemoList items={memo.interestingContributors.quality} empty="No quality contributors surfaced." />
              </div>
              <div>
                <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Mispricing contributors</div>
                <MemoList items={memo.interestingContributors.mispricing} empty="No mispricing contributors surfaced." />
              </div>
            </div>
            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Core block scores</div>
              <MetricGrid items={memo.blockScores.map((item) => ({ label: item.title, value: item.body }))} />
            </div>
          </div>
        </ResearchPanel>

        <ResearchPanel
          title="What Breaks The Thesis"
          subtitle="Negative drags, fragility contributors, and explicit thesis breakers that can invalidate the setup."
        >
          <div className="space-y-5">
            <MemoList items={memo.breaks} empty="No explicit negative drags or thesis breakers surfaced." />
            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Fragility contributors</div>
              <MemoList items={memo.fragilityContributors} empty="No fragility contributors surfaced." />
            </div>
          </div>
        </ResearchPanel>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <ResearchPanel
          title="Confidence And Data Trust"
          subtitle="Confidence profile, conditioning reliability, key uncertainties, and visibility into repaired or discarded inputs."
        >
          <div className="space-y-5">
            <MetricGrid items={memo.confidenceItems.map((item) => ({ label: item.title, value: item.body, meta: item.meta }))} />
            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Key uncertainties</div>
              <MemoList items={memo.uncertainties} empty="No explicit key uncertainties were emitted." />
            </div>
            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Conditioning visibility</div>
              <MetricGrid items={memo.visibilityItems.map((item) => ({ label: item.title, value: item.body, meta: item.meta }))} />
            </div>
          </div>
        </ResearchPanel>

        <ResearchPanel
          title="Stress And Execution"
          subtitle="Fragility class, stress scenarios, and the execution context that matters once the thesis meets real market structure."
        >
          <div className="space-y-5">
            <MetricGrid items={memo.stressItems.map((item) => ({ label: item.title, value: item.body }))} />
            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Stress scenarios</div>
              <MemoList items={memo.scenarioItems} empty="No stress scenarios were provided for this subnet." />
            </div>
          </div>
        </ResearchPanel>
      </div>

      <ResearchPanel
        title="Raw Context"
        subtitle="Classic market and metadata fields stay visible, but after the thesis, break risk, and trust sections."
      >
        <div className="space-y-5">
          <MetricGrid items={memo.rawContext.map((item) => ({ label: item.title, value: item.body }))} />
          <div className="flex flex-wrap gap-2">
            {memo.links.map((link) => (
              <a
                key={link.href}
                href={link.href}
                target="_blank"
                rel="noreferrer"
                className="rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-stone-300 transition-colors hover:bg-white/[0.08]"
              >
                {link.label}
              </a>
            ))}
          </div>
        </div>
      </ResearchPanel>
    </div>
  )
}
