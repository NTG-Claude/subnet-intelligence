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
      <div className="sticky top-16 z-20 hidden grid-cols-[minmax(0,1.35fr)_minmax(320px,0.95fr)_220px] gap-4 rounded-2xl border border-white/10 bg-stone-950/95 px-4 py-3 backdrop-blur md:grid">
        <div>
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Subnet / primary signals</div>
          <div className="mt-1 text-xs text-stone-600">Name, thesis line, label, and the four V2 signals.</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Opportunity / fragility / confidence</div>
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
            className="grid gap-4 rounded-[1.6rem] border border-white/10 bg-[#11161c] p-4 sm:p-5 md:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.95fr)_220px]"
          >
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge tone="neutral">{row.netuidLabel}</StatusBadge>
                {row.statusFlags.map((flag) => (
                  <StatusBadge key={flag.label} tone={flag.tone}>
                    {flag.label}
                  </StatusBadge>
                ))}
              </div>

              <div className="space-y-2">
                <div className="flex flex-wrap items-end gap-3">
                  <Link href={row.href} className="text-2xl font-semibold tracking-tight text-stone-50 transition-colors hover:text-sky-200">
                    {row.name}
                  </Link>
                  <span className="text-sm text-stone-500">{row.decisionLine}</span>
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
              <ResearchLine title="Opportunity" body={row.opportunityRead} items={row.opportunityNotes} />
              <div className="grid gap-3 xl:grid-cols-2">
                <ResearchLine title="Fragility" body={row.fragilityRead} items={row.riskNotes} />
                <ResearchLine title="Confidence" body={row.confidenceRead} items={row.uncertaintyNotes} />
              </div>
              <div className="rounded-2xl border border-white/10 bg-stone-950 p-3">
                <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Quality</div>
                <p className="mt-2 text-sm leading-6 text-stone-300">{row.qualityRead}</p>
              </div>
            </div>

            <div className="flex h-full flex-col rounded-2xl border border-white/10 bg-stone-950 p-4">
              <dl className="space-y-3">
                <div className="flex items-center justify-between gap-3 text-sm">
                  <dt className="text-stone-500">Rank</dt>
                  <dd className="font-medium text-stone-100">{row.rankLabel}</dd>
                </div>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <dt className="text-stone-500">Percentile</dt>
                  <dd className="font-medium text-stone-100">{row.percentileLabel}</dd>
                </div>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <dt className="text-stone-500">Trust</dt>
                  <dd className="font-medium text-stone-100">{row.trustLabel}</dd>
                </div>
                <div className="space-y-1 pt-1">
                  <dt className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Updated</dt>
                  <dd className="text-sm leading-6 text-stone-300">{row.updatedLabel}</dd>
                </div>
              </dl>

              <div className="mt-4 flex flex-col gap-2">
                <Link href={row.href} className="rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2 text-center text-sm text-stone-100 transition-colors hover:bg-white/[0.08]">
                  Open memo
                </Link>
                <button
                  onClick={() => onToggleCompare(row.id)}
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
