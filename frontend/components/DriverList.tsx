'use client'

interface Driver {
  metric: string
  effect: number
  value: number | null
  normalized: number
  category: string
}

interface Props {
  title: string
  tone: 'positive' | 'negative'
  items: Driver[]
}

function prettyMetric(metric: string): string {
  return metric.replaceAll('_', ' ')
}

export default function DriverList({ title, tone, items }: Props) {
  const toneClass = tone === 'positive' ? 'text-emerald-300' : 'text-rose-300'
  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
      <h3 className={`mb-4 text-sm font-semibold uppercase tracking-[0.24em] ${toneClass}`}>{title}</h3>
      <div className="space-y-3">
        {items.length === 0 && <p className="text-sm text-stone-500">No strong drivers recorded.</p>}
        {items.map((item) => (
          <div key={`${item.metric}-${item.effect}`} className="rounded-2xl border border-white/10 bg-black/20 p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-medium capitalize text-stone-200">{prettyMetric(item.metric)}</span>
              <span className={`text-xs font-mono ${toneClass}`}>{item.effect > 0 ? '+' : ''}{item.effect.toFixed(3)}</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-stone-400">
              <span>Value: {item.value == null ? 'n/a' : item.value.toFixed(4)}</span>
              <span>Norm: {item.normalized.toFixed(3)}</span>
              <span>{item.category}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
