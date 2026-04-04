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
    <div className="flex flex-wrap items-center gap-3 border-b border-[color:var(--border-subtle)] pb-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-3">
          <h3 className="text-base font-semibold tracking-tight text-[color:var(--text-primary)]">{category.title}</h3>
          <div className="text-sm font-medium text-[color:var(--text-primary)]">{score}</div>
        </div>
        <div className="mt-2 h-1.5 max-w-[180px] rounded-full bg-[color:rgba(148,163,184,0.14)]">
          <div
            className="h-1.5 rounded-full bg-[linear-gradient(90deg,rgba(74,222,128,0.88),rgba(125,184,255,0.92))]"
            style={{ width: `${barWidth}%` }}
          />
        </div>
      </div>
      <SentimentBadge sentiment={category.sentiment} />
    </div>
  )
}

function IndicatorRow({ indicator }: { indicator: IndicatorRowViewModel }) {
  const scoreLabel = indicator.desirabilityScore == null ? 'n/a' : indicator.desirabilityScore.toFixed(0)

  return (
    <div
      className="flex flex-wrap items-center gap-3 rounded-[var(--radius-md)] px-1 py-2.5 text-sm sm:flex-nowrap"
      title={indicator.helperText}
    >
      <div className="min-w-0 flex-1 text-[color:var(--text-primary)]">{indicator.label}</div>
      <div className="text-xs font-medium tabular-nums text-[color:var(--text-tertiary)]">{scoreLabel}</div>
      <MicroSentimentScale score={indicator.desirabilityScore} />
      <SentimentBadge sentiment={indicator.sentiment} />
    </div>
  )
}

export default function IndicatorStack({ categories }: { categories: IndicatorCategoryViewModel[] }) {
  return (
    <section className="space-y-4">
      {categories.map((category) => (
        <div key={category.key} className="surface-panel p-4 sm:p-5">
          <CompactCategoryHeader category={category} />
          <div className="mt-2 divide-y divide-[color:rgba(148,163,184,0.08)]">
            {category.indicators.map((indicator) => (
              <IndicatorRow key={indicator.key} indicator={indicator} />
            ))}
          </div>
        </div>
      ))}
    </section>
  )
}
