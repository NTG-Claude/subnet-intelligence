'use client'

import Link from 'next/link'

import { UniverseRowViewModel } from '@/lib/view-models/research'
import { HintBadge, SignalPill, StatusBadge, cn } from '@/components/shared/research-ui'

interface Props {
  rows: UniverseRowViewModel[]
  currentLensTitle: string
  emptyMessage: string
  compareIds: number[]
  onToggleCompare: (netuid: number) => void
}

function ResearchLine({
  title,
  body,
  items,
}: {
  title: string
  body: string
  items: { label: string; tone: 'quality' | 'mispricing' | 'fragility' | 'confidence' | 'warning' | 'neutral' }[]
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-stone-950 p-3">
      <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">{title}</div>
      <p className="mt-2 text-sm leading-6 text-stone-300">{body}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.length ? items.map((item) => <HintBadge key={item.label} label={item.label} tone={item.tone} />) : <span className="text-xs text-stone-500">No surfaced detail.</span>}
      </div>
    </div>
  )
}

export default function ResearchList({ rows, currentLensTitle, emptyMessage, compareIds, onToggleCompare }: Props) {
  return (
    <div className="space-y-4">
      <div className="sticky top-16 z-20 hidden grid-cols-[110px_minmax(0,1.2fr)_minmax(280px,0.9fr)_220px] gap-4 rounded-2xl border border-white/10 bg-stone-950/95 px-4 py-3 backdrop-blur lg:grid">
        <div>
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Rank</div>
          <div className="mt-1 text-xs text-stone-600">Classic overall order.</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Subnet / thesis / primary signals</div>
          <div className="mt-1 text-xs text-stone-600">Name, thesis line, and the four V2 signals.</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Support / risks / confidence</div>
          <div className="mt-1 text-xs text-stone-600">Positive drivers, failure modes, and trust markers.</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Memo / compare</div>
          <div className="mt-1 text-xs text-stone-600">Rank, updated state, and workflow actions.</div>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-white/10 bg-stone-950 p-10 text-center">
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">{currentLensTitle}</div>
          <p className="mt-3 text-sm leading-6 text-stone-400">{emptyMessage}</p>
        </div>
      ) : null}

      {rows.map((row) => {
        const selected = compareIds.includes(row.id)
        return (
          <article
            key={row.id}
            className="grid gap-4 rounded-[1.6rem] border border-white/10 bg-[#11161c] p-4 sm:p-5 lg:grid-cols-[110px_minmax(0,1.2fr)_minmax(280px,0.9fr)_220px]"
          >
            <div className="rounded-2xl border border-white/10 bg-stone-950 p-4">
              <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Overall</div>
              <div className="mt-3 text-3xl font-semibold tracking-tight text-stone-50">{row.rankLabel}</div>
              <div className="mt-1 text-sm text-stone-500">{row.percentileLabel} percentile</div>
              <div className="mt-4 space-y-2">
                <StatusBadge tone="neutral">{row.netuidLabel}</StatusBadge>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge tone={row.modelLabelTone}>{row.modelLabel}</StatusBadge>
              </div>

              <div className="space-y-2">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <Link href={row.href} className="text-2xl font-semibold tracking-tight text-stone-50 transition-colors hover:text-sky-200">
                      {row.name}
                    </Link>
                    <div className="mt-2 text-sm text-stone-500">{row.decisionLine}</div>
                  </div>
                  <div className="min-w-[164px] rounded-2xl border border-white/10 bg-stone-950 px-3 py-2 text-right">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-stone-500">Model label</div>
                    <div className="mt-1 text-sm font-medium text-stone-100">{row.modelLabel}</div>
                  </div>
                </div>
                <p className="max-w-4xl text-sm leading-6 text-stone-400">{row.thesisLine}</p>
              </div>

              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                {row.signals.map((signal) => (
                  <SignalPill key={signal.key} signal={signal} compact />
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <ResearchLine title="Why it earns attention" body={row.opportunityRead} items={row.opportunityNotes} />
              <div className="grid gap-3 xl:grid-cols-2">
                <ResearchLine title="What can break it" body={row.fragilityRead} items={row.riskNotes} />
                <ResearchLine title="What is still uncertain" body={row.confidenceRead} items={row.uncertaintyNotes} />
              </div>
              <div className="rounded-2xl border border-white/10 bg-stone-950 p-3">
                <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Quality read</div>
                <p className="mt-2 text-sm leading-6 text-stone-300">{row.qualityRead}</p>
              </div>
            </div>

            <div className="flex h-full flex-col rounded-2xl border border-white/10 bg-stone-950 p-4">
              <dl className="space-y-3">
                <div className="space-y-1 pt-1">
                  <dt className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Updated</dt>
                  <dd className="text-sm leading-6 text-stone-300">{row.updatedLabel}</dd>
                </div>
                <div className="rounded-2xl border border-white/10 bg-[#131922] p-3">
                  <dt className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Decision framing</dt>
                  <dd className="mt-2 text-sm leading-6 text-stone-300">{row.decisionLine}</dd>
                </div>
              </dl>

              <div className="mt-4 flex flex-col gap-2">
                <Link href={row.href} className="rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2 text-center text-sm text-stone-100 transition-colors hover:bg-white/[0.08]">
                  Open memo
                </Link>
                <button
                  onClick={() => onToggleCompare(row.id)}
                  aria-pressed={selected}
                  className={cn(
                    'rounded-2xl border px-3 py-2 text-sm transition-colors',
                    selected
                      ? 'border-sky-500/30 bg-sky-500/10 text-sky-200'
                      : 'border-white/10 bg-stone-900 text-stone-300 hover:bg-white/[0.08]',
                  )}
                >
                  {selected ? 'In compare tray' : row.compareLabel}
                </button>
              </div>
            </div>
          </article>
        )
      })}
    </div>
  )
}
