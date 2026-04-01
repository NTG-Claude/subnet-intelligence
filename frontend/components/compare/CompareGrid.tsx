import Link from 'next/link'

import { DetailMemoViewModel } from '@/lib/view-models/research'
import { MemoList, SignalPill, StatusBadge } from '@/components/shared/research-ui'

export default function CompareGrid({ memos }: { memos: DetailMemoViewModel[] }) {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Link href="/" className="inline-flex items-center text-sm text-stone-400 transition-colors hover:text-stone-100">
          Back to universe
        </Link>
        <div>
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Compare</div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-stone-50">Side-by-side V2 analysis</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-400">
            Compare primary signals, core blocks, drivers and drags, confidence profile, and stress readouts without collapsing back into one composite score.
          </p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {memos.map((memo) => (
          <section key={memo.netuidLabel} className="rounded-3xl border border-white/10 bg-[#11161c] p-5">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone="neutral">{memo.netuidLabel}</StatusBadge>
              {memo.summaryFlags.map((flag) => (
                <StatusBadge key={flag.label} tone={flag.tone}>
                  {flag.label}
                </StatusBadge>
              ))}
            </div>
            <div className="mt-4 space-y-2">
              <Link href={memo.href} className="text-2xl font-semibold tracking-tight text-stone-50 transition-colors hover:text-sky-200">
                {memo.name}
              </Link>
              <p className="text-sm leading-6 text-stone-400">{memo.decisionLine}</p>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {memo.signals.map((signal) => (
                <SignalPill key={signal.key} signal={signal} compact />
              ))}
            </div>

            <div className="mt-5 grid gap-5 lg:grid-cols-2">
              <div>
                <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Top drivers</div>
                <MemoList items={memo.interesting.slice(0, 3)} empty="No positive drivers surfaced." />
              </div>
              <div>
                <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Top drags</div>
                <MemoList items={memo.breaks.slice(0, 3)} empty="No negative drags surfaced." />
              </div>
            </div>

            <div className="mt-5 grid gap-5 lg:grid-cols-2">
              <div>
                <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Confidence profile</div>
                <MemoList
                  items={memo.confidenceHeadline.map((item) => ({
                    title: item.label,
                    body: item.value,
                    tone: item.tone,
                    meta: item.meta,
                  }))}
                  empty="No confidence readout."
                />
              </div>
              <div>
                <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-stone-500">Stress profile</div>
                <MemoList items={[...memo.stressItems, ...memo.scenarioItems].slice(0, 4)} empty="No stress readout." />
              </div>
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
