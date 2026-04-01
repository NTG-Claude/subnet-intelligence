import Link from 'next/link'

import { DetailMemoViewModel, MemoSectionItem } from '@/lib/view-models/research'
import { MemoList, MetricGrid, ResearchPanel, SignalPill, StatusBadge } from '@/components/shared/research-ui'

function MetricList({ items }: { items: MemoSectionItem[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <div key={`${item.title}-${item.body}`} className="rounded-2xl border border-white/10 bg-stone-950 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">{item.title}</div>
          <div className="mt-2 text-lg font-semibold text-stone-100">{item.body}</div>
          {item.meta ? <div className="mt-1 text-xs text-stone-500">{item.meta}</div> : null}
        </div>
      ))}
    </div>
  )
}

export default function SubnetResearchMemo({ memo }: { memo: DetailMemoViewModel }) {
  return (
    <div className="space-y-6">
      <Link href="/" className="inline-flex items-center text-sm text-stone-400 transition-colors hover:text-stone-100">
        Back to universe
      </Link>

      <section className="rounded-[2rem] border border-white/10 bg-[#10151b] p-5 sm:p-6">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_360px]">
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone="neutral">{memo.netuidLabel}</StatusBadge>
              {memo.summaryFlags.map((flag) => (
                <StatusBadge key={flag.label} tone={flag.tone}>
                  {flag.label}
                </StatusBadge>
              ))}
            </div>

            <div className="space-y-3">
              <div className="flex flex-wrap items-end gap-4">
                <h1 className="text-3xl font-semibold tracking-tight text-stone-50 sm:text-4xl">{memo.name}</h1>
                <div className="text-sm text-stone-500">Updated {memo.updatedLabel}</div>
              </div>
              <p className="max-w-4xl text-base leading-7 text-stone-300">{memo.thesis}</p>
              <div className="rounded-2xl border border-sky-500/20 bg-sky-500/[0.05] p-4 text-sm leading-6 text-stone-300">
                <div className="text-[11px] uppercase tracking-[0.24em] text-sky-200">Decision framing</div>
                <div className="mt-2">{memo.decisionLine}</div>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {memo.signals.map((signal) => (
                <SignalPill key={signal.key} signal={signal} />
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-3xl border border-white/10 bg-stone-950 p-4">
              <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Investment summary</div>
              <div className="mt-4">
                <MetricGrid items={memo.summaryMetrics} />
              </div>
            </div>

            <div className="rounded-3xl border border-violet-500/20 bg-violet-500/[0.05] p-4">
              <div className="text-[11px] uppercase tracking-[0.24em] text-violet-200">How to read this memo</div>
              <div className="mt-3 space-y-3 text-sm leading-6 text-stone-300">
                <p>Start with the thesis and the four primary signals. Then check whether the positive case survives the failure modes and confidence sections.</p>
                <p>Only treat the raw market context as supporting evidence. It should not be the first decision input.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <ResearchPanel
        title="Why This Is Interesting"
        subtitle="Top positive drivers, primary signal contributors, and block scores that support the case."
        className="bg-[#10151b]"
      >
        <div className="space-y-5">
          <MemoList items={memo.interesting} empty="No top positive drivers were emitted for this subnet." />
          <div className="grid gap-5 xl:grid-cols-2">
            {memo.signalContributorSections.map((section) => (
              <div key={section.title}>
                <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">{section.title}</div>
                <MemoList items={section.items} empty={`No ${section.title.toLowerCase()} surfaced.`} />
              </div>
            ))}
          </div>
          <div>
            <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Block scores</div>
            <MetricList items={memo.blockScores} />
          </div>
        </div>
      </ResearchPanel>

      <ResearchPanel
        title="What Breaks The Thesis"
        subtitle="Negative drags, thesis breakers, and fragility contributors that can invalidate the setup."
        className="bg-[#10151b]"
      >
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <div>
            <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Failure modes</div>
            <MemoList items={memo.breaks} empty="No explicit failure modes were emitted for this subnet." />
          </div>
          <div>
            <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Fragility contributors</div>
            <MemoList items={memo.fragilityContributors} empty="No fragility contributors surfaced." />
          </div>
        </div>
      </ResearchPanel>

      <ResearchPanel
        title="Confidence And Data Trust"
        subtitle="Confidence profile, conditioning reliability, reconstructed or discarded inputs, and the uncertainties that can still move the memo."
        className="bg-[#10151b]"
      >
        <div className="space-y-5">
          <MetricGrid items={memo.confidenceHeadline} />
          <div className="rounded-2xl border border-amber-500/20 bg-amber-500/[0.05] p-4 text-sm leading-6 text-stone-300">
            <div className="text-[11px] uppercase tracking-[0.24em] text-amber-200">Trust interpretation</div>
            <p className="mt-2">
              Reliability shows how complete and stable the input evidence was. Visibility tells us whether the model had to reconstruct, bound, or discard parts of the underlying telemetry.
            </p>
          </div>
          <div className="grid gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Conditioning reliability</div>
              <MemoList items={memo.confidenceItems} empty="No conditioning reliability data was emitted." />
            </div>
            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Key uncertainties</div>
              <MemoList items={memo.uncertainties} empty="No key uncertainties were emitted." />
            </div>
          </div>
          <div>
            <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Conditioning visibility</div>
            <MetricList items={memo.visibilityItems} />
          </div>
        </div>
      </ResearchPanel>

      <ResearchPanel
        title="Stress And Execution"
        subtitle="Fragility class, drawdown scenarios, and the raw execution context once the thesis meets real market structure."
        className="bg-[#10151b]"
      >
        <div className="space-y-5">
          <MetricList items={memo.stressItems} />
          <div>
            <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Stress scenarios</div>
            <MemoList items={memo.scenarioItems} empty="No stress scenarios were provided for this subnet." />
          </div>
        </div>
      </ResearchPanel>

      <ResearchPanel
        title="Raw Context"
        subtitle="Classic market fields stay available, but only after the thesis, break risk, and trust sections."
        className="bg-[#10151b]"
      >
        <details className="group rounded-2xl border border-white/10 bg-stone-950 p-4 open:border-white/15">
          <summary className="cursor-pointer list-none text-sm font-medium text-stone-200">
            Expand raw market context and external links
          </summary>
          <div className="mt-5 space-y-5">
            <MetricList items={memo.rawContext} />
            <div className="flex flex-wrap gap-2">
              {memo.links.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-2xl border border-white/10 bg-[#131922] px-3 py-2 text-sm text-stone-300 transition-colors hover:bg-white/[0.08]"
                >
                  {link.label}
                </a>
              ))}
            </div>
          </div>
        </details>
      </ResearchPanel>
    </div>
  )
}
