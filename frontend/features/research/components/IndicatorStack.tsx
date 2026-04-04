import {
  IndicatorCategoryViewModel,
  IndicatorRowViewModel,
} from '@/lib/view-models/research'

import MicroSentimentScale from './MicroSentimentScale'
import SentimentBadge from './SentimentBadge'

function CompactCategoryHeader({ category }: { category: IndicatorCategoryViewModel }) {
  const score = category.displayScore == null ? 'n/a' : category.displayScore.toFixed(1)
  const barWidth = category.displayScore == null ? 18 : Math.max(10, Math.min(100, category.displayScore))

  return (
    <div className="border-b border-[color:rgba(148,163,184,0.1)] pb-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-3">
            <h3 className="text-[1.55rem] font-semibold tracking-tight text-[color:var(--text-primary)]">{category.title}</h3>
            <div className="text-lg font-semibold tabular-nums text-[color:rgba(226,232,240,0.94)]">{score}</div>
          </div>
          <div className="mt-3 h-1.5 max-w-[260px] rounded-full bg-[color:rgba(71,85,105,0.38)]">
            <div
              className="h-1.5 rounded-full bg-[linear-gradient(90deg,rgba(74,222,128,0.9),rgba(96,165,250,0.9))]"
              style={{ width: `${barWidth}%` }}
            />
          </div>
        </div>
        <div className="pt-1">
          <SentimentBadge sentiment={category.sentiment} />
        </div>
      </div>
    </div>
  )
}

function IndicatorRow({ indicator }: { indicator: IndicatorRowViewModel }) {
  const scoreLabel = indicator.desirabilityScore == null ? 'n/a' : indicator.desirabilityScore.toFixed(0)

  return (
    <div
      className="flex flex-wrap items-center gap-x-4 gap-y-3 rounded-[18px] px-1 py-4 text-sm transition-colors duration-150 hover:bg-[color:rgba(15,23,42,0.28)] md:grid md:grid-cols-[minmax(0,1fr)_44px_132px_auto] md:gap-4"
      title={indicator.helperText}
    >
      <div className="min-w-0 flex-[1_1_260px] text-[1.02rem] font-medium text-[color:rgba(226,232,240,0.96)]">{indicator.label}</div>
      <div className="text-sm font-semibold tabular-nums text-[color:rgba(148,163,184,0.78)] md:text-right">{scoreLabel}</div>
      <div className="ml-auto md:ml-0">
        <MicroSentimentScale score={indicator.desirabilityScore} />
      </div>
      <div className="md:justify-self-end">
        <SentimentBadge sentiment={indicator.sentiment} />
      </div>
    </div>
  )
}

export default function IndicatorStack({ categories }: { categories: IndicatorCategoryViewModel[] }) {
  return (
    <section className="space-y-5">
      {categories.map((category) => (
        <div
          key={category.key}
          className="overflow-hidden rounded-[32px] border border-[color:rgba(148,163,184,0.12)] bg-[linear-gradient(180deg,rgba(18,30,42,0.96),rgba(15,25,36,0.98))] px-6 py-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.02)] sm:px-7 sm:py-6"
        >
          <CompactCategoryHeader category={category} />
          <div className="mt-4 divide-y divide-[color:rgba(148,163,184,0.06)]">
            {category.indicators.map((indicator) => (
              <IndicatorRow key={indicator.key} indicator={indicator} />
            ))}
          </div>
        </div>
      ))}
    </section>
  )
}
