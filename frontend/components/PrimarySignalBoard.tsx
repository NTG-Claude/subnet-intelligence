'use client'

import Link from 'next/link'
import { PrimaryOutputs, SubnetSummary } from '@/lib/api'

interface SignalCardConfig {
  keyName: keyof PrimaryOutputs
  title: string
  subtitle: string
  invert?: boolean
  accent: string
}

const CARDS: SignalCardConfig[] = [
  {
    keyName: 'fundamental_quality',
    title: 'Best Fundamental Quality',
    subtitle: 'Highest earned structural quality',
    accent: 'from-emerald-400 to-lime-300',
  },
  {
    keyName: 'mispricing_signal',
    title: 'Best Mispricing Setup',
    subtitle: 'Strongest expectation gap versus price',
    accent: 'from-sky-400 to-cyan-300',
  },
  {
    keyName: 'fragility_risk',
    title: 'Lowest Fragility',
    subtitle: 'Most resilient structures under stress',
    invert: true,
    accent: 'from-amber-300 to-orange-400',
  },
  {
    keyName: 'signal_confidence',
    title: 'Highest Confidence',
    subtitle: 'Cleanest evidence quality and freshness',
    accent: 'from-fuchsia-400 to-rose-300',
  },
]

function metricLabel(keyName: keyof PrimaryOutputs): string {
  if (keyName === 'fundamental_quality') return 'FQ'
  if (keyName === 'mispricing_signal') return 'MP'
  if (keyName === 'fragility_risk') return 'FR'
  return 'CF'
}

function valueOf(subnet: SubnetSummary, keyName: keyof PrimaryOutputs): number {
  return subnet.primary_outputs?.[keyName] ?? 0
}

export default function PrimarySignalBoard({ subnets }: { subnets: SubnetSummary[] }) {
  return (
    <div className="grid gap-4 xl:grid-cols-4">
      {CARDS.map((card) => {
        const ranked = [...subnets]
          .filter((subnet) => subnet.primary_outputs)
          .sort((left, right) => {
            const a = valueOf(left, card.keyName)
            const b = valueOf(right, card.keyName)
            return card.invert ? a - b : b - a
          })
          .slice(0, 5)

        return (
          <div key={card.keyName} className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5">
            <div className="mb-4">
              <div className={`inline-flex rounded-full bg-gradient-to-r ${card.accent} px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-stone-950`}>
                {metricLabel(card.keyName)}
              </div>
              <h3 className="mt-3 text-base font-semibold text-stone-100">{card.title}</h3>
              <p className="mt-1 text-sm text-stone-500">{card.subtitle}</p>
            </div>
            <div className="space-y-2">
              {ranked.map((subnet, index) => (
                <Link
                  key={`${card.keyName}-${subnet.netuid}`}
                  href={`/subnets/${subnet.netuid}`}
                  className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/20 px-3 py-2 transition-colors hover:bg-white/10"
                >
                  <div className="min-w-0">
                    <div className="text-xs uppercase tracking-[0.2em] text-stone-500">#{index + 1} SN{subnet.netuid}</div>
                    <div className="truncate text-sm font-medium text-stone-100">{subnet.name ?? `Subnet ${subnet.netuid}`}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-semibold text-stone-100">{valueOf(subnet, card.keyName).toFixed(0)}</div>
                    <div className="text-[11px] text-stone-500">{subnet.label ?? 'Under Review'}</div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
