'use client'

import { DriverItem } from '@/lib/api'

interface Props {
  title: string
  subtitle: string
  supports?: DriverItem[]
  headwinds?: DriverItem[]
  bullets?: string[]
}

function prettyMetric(metric: string): string {
  return metric.replaceAll('_', ' ')
}

export default function ThesisPanel({ title, subtitle, supports = [], headwinds = [], bullets = [] }: Props) {
  return (
    <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5">
      <div className="mb-4">
        <h3 className="text-base font-semibold text-stone-100">{title}</h3>
        <p className="mt-1 text-sm text-stone-500">{subtitle}</p>
      </div>

      {(supports.length > 0 || headwinds.length > 0) && (
        <div className="grid gap-3 lg:grid-cols-2">
          <div className="space-y-2">
            <div className="text-xs uppercase tracking-[0.24em] text-emerald-300">Supports</div>
            {supports.length === 0 && <div className="rounded-2xl border border-white/10 bg-black/20 p-3 text-sm text-stone-500">No clear supporting drivers recorded.</div>}
            {supports.map((item) => (
              <div key={`${title}-support-${item.metric}-${item.effect}`} className="rounded-2xl border border-white/10 bg-black/20 p-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium capitalize text-stone-200">{prettyMetric(item.metric)}</span>
                  <span className="text-xs font-mono text-emerald-300">+{item.effect.toFixed(3)}</span>
                </div>
                <div className="mt-2 text-xs text-stone-400">{item.category}</div>
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <div className="text-xs uppercase tracking-[0.24em] text-rose-300">Headwinds</div>
            {headwinds.length === 0 && <div className="rounded-2xl border border-white/10 bg-black/20 p-3 text-sm text-stone-500">No major headwinds recorded.</div>}
            {headwinds.map((item) => (
              <div key={`${title}-headwind-${item.metric}-${item.effect}`} className="rounded-2xl border border-white/10 bg-black/20 p-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium capitalize text-stone-200">{prettyMetric(item.metric)}</span>
                  <span className="text-xs font-mono text-rose-300">{item.effect.toFixed(3)}</span>
                </div>
                <div className="mt-2 text-xs text-stone-400">{item.category}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {bullets.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="text-xs uppercase tracking-[0.24em] text-amber-200">Thesis Breakers</div>
          {bullets.map((bullet) => (
            <div key={bullet} className="rounded-2xl border border-amber-300/15 bg-amber-300/5 p-3 text-sm text-stone-300">
              {bullet}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
