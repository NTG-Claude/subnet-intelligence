'use client'

import { ReactNode, useEffect, useRef, useState } from 'react'

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
  id,
  title,
  subtitle,
  children,
  className,
}: {
  id?: string
  title: string
  subtitle?: string
  children: ReactNode
  className?: string
}) {
  return (
    <section id={id} className={cn('rounded-3xl border border-white/10 bg-[#11161c] p-5 sm:p-6', className)}>
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

/* ─── New compact components for the redesigned list ─── */

const SIGNAL_DESCRIPTIONS: Record<string, string> = {
  Quality: 'Fundamental quality of the subnet based on network health, activity, and development.',
  Mispricing: 'Gap between intrinsic quality and current market valuation.',
  Fragility: 'Risk that the thesis breaks under stress or poor execution. Lower is better.',
  Confidence: 'Trust in the underlying data and evidence mix.',
}

export function SparkSignalBar({ signal }: { signal: SignalStat }) {
  const rawValue = signal.value
  const display = rawValue == null ? '—' : rawValue.toFixed(0)
  const width = rawValue == null ? 0 : Math.max(4, Math.min(100, signal.invert ? 100 - rawValue : rawValue))

  return (
    <div className="group relative flex items-center gap-2 min-w-0">
      <span className="text-[10px] uppercase tracking-[0.16em] text-stone-500 w-8 shrink-0">{signal.shortLabel}</span>
      <div className="relative h-1 w-12 shrink-0 rounded-full bg-white/[0.06]">
        <div
          className={cn('absolute inset-y-0 left-0 rounded-full transition-all', trackClasses(signal.tone))}
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="font-mono text-[11px] font-medium text-stone-300 w-6 text-right">{display}</span>
      <div className="pointer-events-none absolute -top-9 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-lg bg-stone-800 px-2.5 py-1 text-[11px] text-stone-200 opacity-0 shadow-lg transition-opacity group-hover:opacity-100 z-50">
        {SIGNAL_DESCRIPTIONS[signal.label] ?? signal.label}
      </div>
    </div>
  )
}

export function SignalProfileSVG({ signals }: { signals: SignalStat[] }) {
  const barWidth = 6
  const gap = 2
  const maxHeight = 20
  const totalWidth = signals.length * barWidth + (signals.length - 1) * gap

  const toneToColor: Record<string, string> = {
    quality: '#34d399',
    mispricing: '#38bdf8',
    fragility: '#fb7185',
    confidence: '#a78bfa',
    warning: '#fbbf24',
    neutral: '#78716c',
  }

  return (
    <svg width={totalWidth} height={maxHeight} viewBox={`0 0 ${totalWidth} ${maxHeight}`} className="shrink-0">
      {signals.map((signal, i) => {
        const raw = signal.value ?? 0
        const val = signal.invert ? 100 - raw : raw
        const h = Math.max(2, (val / 100) * maxHeight)
        const x = i * (barWidth + gap)
        return (
          <rect
            key={signal.key}
            x={x}
            y={maxHeight - h}
            width={barWidth}
            height={h}
            rx={1.5}
            fill={toneToColor[signal.tone] ?? toneToColor.neutral}
            opacity={0.85}
          />
        )
      })}
    </svg>
  )
}

export function Skeleton({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return <div className={cn('animate-pulse rounded-2xl bg-white/[0.04]', className)} style={style} />
}

export function DropdownPill({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: { id: string; title: string; description?: string }[]
  onChange: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const selected = options.find((o) => o.id === value)

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'focus-ring flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
          open
            ? 'border-white/20 bg-white/[0.08] text-stone-100'
            : 'border-white/10 bg-stone-950 text-stone-400 hover:border-white/20 hover:text-stone-200',
        )}
      >
        <span className="text-stone-500">{label}:</span>
        <span>{selected?.title ?? value}</span>
        <svg width="10" height="10" viewBox="0 0 10 10" className={cn('transition-transform', open && 'rotate-180')}>
          <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="absolute top-full left-0 z-50 mt-1.5 w-72 rounded-2xl border border-white/10 bg-stone-900 p-1.5 shadow-2xl">
          {options.map((opt) => (
            <button
              key={opt.id}
              onClick={() => {
                onChange(opt.id)
                setOpen(false)
              }}
              className={cn(
                'w-full rounded-xl px-3 py-2.5 text-left transition-colors',
                opt.id === value ? 'bg-white/[0.08] text-stone-100' : 'text-stone-400 hover:bg-white/[0.04] hover:text-stone-200',
              )}
            >
              <div className="text-xs font-medium">{opt.title}</div>
              {opt.description ? <div className="mt-0.5 text-[11px] leading-4 text-stone-500">{opt.description}</div> : null}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function Breadcrumb({ items }: { items: { label: string; href?: string }[] }) {
  return (
    <nav className="flex items-center gap-1.5 text-sm text-stone-500">
      {items.map((item, i) => (
        <span key={`${item.label}-${i}`} className="flex items-center gap-1.5">
          {i > 0 && <span className="text-stone-600">/</span>}
          {item.href ? (
            <a href={item.href} className="transition-colors hover:text-stone-100">
              {item.label}
            </a>
          ) : (
            <span className="text-stone-300">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}

export function ChevronIcon({ expanded, className }: { expanded: boolean; className?: string }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      className={cn('transition-transform duration-200', expanded && 'rotate-180', className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 6L8 10L12 6" />
    </svg>
  )
}
