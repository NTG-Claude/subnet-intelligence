'use client'

import Link from 'next/link'

import { SubnetSummary } from '@/lib/api'
import { buildSignalViews } from '@/lib/signalSelection'

export default function PrimarySignalBoard({ subnets }: { subnets: SubnetSummary[] }) {
  const views = buildSignalViews(subnets)

  return (
    <div className="grid gap-4 xl:grid-cols-5">
      {views.map((view) => (
        <div key={view.id} className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5">
          <div className="mb-4">
            <div
              className={`inline-flex rounded-full bg-gradient-to-r ${view.accent} px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-stone-950`}
            >
              View
            </div>
            <h3 className="mt-3 text-base font-semibold text-stone-100">{view.title}</h3>
            <p className="mt-1 text-sm text-stone-500">{view.subtitle}</p>
          </div>
          <div className="space-y-2">
            {view.subnets.map((subnet, index) => (
              <Link
                key={`${view.id}-${subnet.netuid}`}
                href={`/subnets/${subnet.netuid}`}
                className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/20 px-3 py-2 transition-colors hover:bg-white/10"
              >
                <div className="min-w-0">
                  <div className="text-xs uppercase tracking-[0.2em] text-stone-500">#{index + 1} SN{subnet.netuid}</div>
                  <div className="truncate text-sm font-medium text-stone-100">{subnet.name ?? `Subnet ${subnet.netuid}`}</div>
                  <div className="mt-1 text-[11px] text-stone-500">
                    Pool {(subnet.tao_in_pool ?? 0).toLocaleString('en-US', { maximumFractionDigits: 0 })} - APY{' '}
                    {subnet.staking_apy != null ? `${subnet.staking_apy.toFixed(0)}%` : 'n/a'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold text-stone-100">
                    MP {subnet.primary_outputs?.mispricing_signal.toFixed(0)} - CF {subnet.primary_outputs?.signal_confidence.toFixed(0)}
                  </div>
                  <div className="text-[11px] text-stone-500">{subnet.label ?? 'Under Review'}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
