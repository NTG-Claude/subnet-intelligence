import { ReactNode } from 'react'

import { SignalStat, SignalTone } from '@/lib/view-models/research'

export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(' ')
}

function toneClasses(tone: SignalTone): string {
  switch (tone) {
    case 'quality':
      return 'border-emerald-500/20 bg-emerald-500/10 text-emerald-200'
    case 'mispricing':
      return 'border-sky-500/20 bg-sky-500/10 text-sky-200'
    case 'fragility':
      return 'border-rose-500/20 bg-rose-500/10 text-rose-200'
    case 'confidence':
      return 'border-violet-500/20 bg-violet-500/10 text-violet-200'
    case 'warning':
      return 'border-amber-500/20 bg-amber-500/10 text-amber-200'
    default:
      return 'border-white/10 bg-white/[0.03] text-stone-300'
  }
}

function trackClasses(tone: SignalTone): string {
  switch (tone) {
    case 'quality':
      return 'bg-emerald-400'
    case 'mispricing':
      return 'bg-sky-400'
    case 'fragility':
      return 'bg-rose-400'
    case 'confidence':
      return 'bg-violet-400'
    case 'warning':
      return 'bg-amber-400'
    default:
      return 'bg-stone-400'
  }
}

export function ResearchPanel({
  title,
  subtitle,
  children,
  className,
}: {
  title: string
  subtitle?: string
  children: ReactNode
  className?: string
}) {
  return (
    <section className={cn('rounded-3xl border border-white/10 bg-[#11161c] p-5 sm:p-6', className)}>
      <div className="mb-4 space-y-1">
        <div className="text-[11px] font-medium uppercase tracking-[0.28em] text-stone-500">{title}</div>
        {subtitle ? <p className="max-w-3xl text-sm leading-6 text-stone-400">{subtitle}</p> : null}
      </div>
      {children}
    </section>
  )
}

export function StatusBadge({ children, tone = 'neutral' }: { children: ReactNode; tone?: SignalTone }) {
  return (
    <span className={cn('inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-medium uppercase tracking-[0.18em]', toneClasses(tone))}>
      {children}
    </span>
  )
}

export function SignalPill({ signal, compact = false }: { signal: SignalStat; compact?: boolean }) {
  const rawValue = signal.value
  const display = rawValue == null ? 'n/a' : rawValue.toFixed(1)
  const width = rawValue == null ? 0 : Math.max(5, Math.min(100, signal.invert ? 100 - rawValue : rawValue))

  return (
    <div className={cn('rounded-2xl border border-white/10 bg-stone-950', compact ? 'p-2.5' : 'p-3')}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-[11px] uppercase tracking-[0.24em] text-stone-500">{signal.label}</span>
        <span className="text-sm font-semibold text-stone-100">{display}</span>
      </div>
      <div className="mt-2 h-1.5 rounded-full bg-white/5">
        <div className={cn('h-1.5 rounded-full', trackClasses(signal.tone))} style={{ width: `${width}%` }} />
      </div>
    </div>
  )
}

export function HintBadge({ label, tone }: { label: string; tone: SignalTone }) {
  return (
    <span className={cn('inline-flex items-center rounded-full border px-2.5 py-1 text-xs leading-5', toneClasses(tone))}>
      {label}
    </span>
  )
}

export function MetricGrid({
  items,
  dense = false,
}: {
  items: { label: string; value: string; tone?: SignalTone; meta?: string }[]
  dense?: boolean
}) {
  return (
    <div className={cn('grid gap-3', dense ? 'sm:grid-cols-2 xl:grid-cols-5' : 'sm:grid-cols-2 xl:grid-cols-4')}>
      {items.map((item) => (
        <div key={`${item.label}-${item.value}`} className="rounded-2xl border border-white/10 bg-stone-950 p-4">
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">{item.label}</div>
          <div className="mt-2 text-lg font-semibold text-stone-100">{item.value}</div>
          {item.meta ? <div className="mt-1 text-xs text-stone-500">{item.meta}</div> : null}
        </div>
      ))}
    </div>
  )
}

export function MemoList({
  items,
  empty,
}: {
  items: { title: string; body: string; tone?: SignalTone; score?: number | null; meta?: string }[]
  empty: string
}) {
  if (!items.length) {
    return <div className="rounded-2xl border border-dashed border-white/10 bg-stone-950 p-4 text-sm text-stone-500">{empty}</div>
  }

  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div key={`${item.title}-${index}`} className="rounded-2xl border border-white/10 bg-stone-950 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="text-sm font-medium text-stone-100">{item.title}</div>
              <p className="text-sm leading-6 text-stone-400">{item.body}</p>
            </div>
            {item.score != null ? <StatusBadge tone={item.tone}>{item.score.toFixed(1)}</StatusBadge> : null}
          </div>
          {item.meta ? <div className="mt-2 text-xs uppercase tracking-[0.2em] text-stone-500">{item.meta}</div> : null}
        </div>
      ))}
    </div>
  )
}
