'use client'

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { MarketOverviewData } from '@/lib/api'
import { cn, formatCompactNumber } from '@/lib/formatting'

function formatMarketCap(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B tao`
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M tao`
  return `${formatCompactNumber(value, 0)} tao`
}

function formatAxisDate(value: string): string {
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(new Date(value))
}

function formatTooltipDate(value: string): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

function MarketTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ value?: number }>
  label?: string
}) {
  if (!active || !payload?.length || typeof payload[0]?.value !== 'number' || !label) return null

  return (
    <div className="rounded-[var(--radius-md)] border border-[color:var(--border-subtle)] bg-[color:rgba(7,14,20,0.96)] p-3 shadow-2xl">
      <div className="text-xs uppercase tracking-[0.18em] text-[color:var(--text-tertiary)]">{formatTooltipDate(label)}</div>
      <div className="mt-2 text-sm text-[color:var(--text-secondary)]">Combined subnet market cap</div>
      <div className="mt-1 text-lg font-semibold text-[color:var(--text-primary)]">{formatMarketCap(payload[0].value)}</div>
    </div>
  )
}

export default function DiscoverMarketHero({
  market,
  lastRun,
}: {
  market: MarketOverviewData
  lastRun: string | null
}) {
  const latestValue = market.current_market_cap_tao
  const change = market.change_pct_vs_previous_run
  const positive = (change ?? 0) >= 0
  const hasHistory = market.points.length > 1

  return (
    <section className="surface-panel overflow-hidden p-0">
      <div className="grid gap-0 xl:grid-cols-[420px_minmax(0,1fr)]">
        <div className="flex flex-col justify-between p-6 sm:p-8">
          <div>
            <p className="eyebrow">Subnet Intelligence</p>
            <div className="mt-5 flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[color:rgba(245,247,250,0.96)] text-lg font-semibold text-[#101820]">
                S
              </div>
              <div>
                <div className="text-3xl font-semibold tracking-tight text-[color:var(--text-primary)]">Subnet Market</div>
                <div className="mt-1 text-sm text-[color:var(--text-tertiary)]">Combined market cap across all tracked subnets</div>
              </div>
            </div>

            <div className="mt-8 flex flex-wrap items-end gap-4">
              <div className="text-5xl font-semibold tracking-tight text-[color:var(--text-primary)] sm:text-6xl">
                {formatMarketCap(latestValue)}
              </div>
              {change != null ? (
                <div
                  className={cn(
                    'mb-1 inline-flex items-center rounded-full px-4 py-2 text-lg font-semibold',
                    positive
                      ? 'bg-[color:rgba(49,164,121,0.14)] text-[color:var(--success-strong)]'
                      : 'bg-[color:rgba(211,87,68,0.16)] text-[color:var(--warning-strong)]',
                  )}
                >
                  {positive ? '+' : ''}
                  {change.toFixed(2)}%
                </div>
              ) : null}
            </div>
          </div>

          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            <div className="surface-subtle p-4">
              <div className="eyebrow">Tracked subnets</div>
              <div className="mt-3 text-2xl font-semibold text-[color:var(--text-primary)]">{market.current_subnet_count}</div>
            </div>
            <div className="surface-subtle p-4">
              <div className="eyebrow">Last run</div>
              <div className="mt-3 text-sm leading-6 text-[color:var(--text-primary)]">
                {lastRun ? lastRun.slice(0, 16).replace('T', ' ') : 'No completed run'}
              </div>
            </div>
          </div>
        </div>

        <div className="relative min-h-[340px] border-t border-[color:var(--border-subtle)] xl:min-h-[460px] xl:border-l xl:border-t-0">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(0,236,214,0.14),_transparent_42%),linear-gradient(180deg,rgba(10,16,20,0.3),rgba(10,16,20,0))]" />
          <div className="relative h-full p-4 sm:p-6">
            {hasHistory ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={market.points} margin={{ top: 12, right: 8, left: 0, bottom: 4 }}>
                  <defs>
                    <linearGradient id="marketHeroFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#00e6d6" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#00e6d6" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(138, 163, 184, 0.12)" vertical={false} />
                  <XAxis
                    dataKey="computed_at"
                    tickFormatter={formatAxisDate}
                    minTickGap={28}
                    stroke="rgba(138, 163, 184, 0.45)"
                    tick={{ fontSize: 11, fill: 'rgba(138, 163, 184, 0.72)' }}
                  />
                  <YAxis
                    tickFormatter={formatMarketCap}
                    width={78}
                    stroke="rgba(138, 163, 184, 0.45)"
                    tick={{ fontSize: 11, fill: 'rgba(138, 163, 184, 0.72)' }}
                  />
                  <Tooltip content={<MarketTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="total_market_cap_tao"
                    stroke="#00e6d6"
                    strokeWidth={2}
                    fill="url(#marketHeroFill)"
                    dot={false}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center rounded-[var(--radius-lg)] border border-dashed border-[color:var(--border-subtle)] bg-[color:rgba(10,18,26,0.42)] px-6 text-center">
                <div>
                  <div className="text-sm font-medium text-[color:var(--text-primary)]">Current market cap loaded</div>
                  <div className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">
                    Historical market-cap points are not available yet, so the trend chart will appear once that run history is exposed.
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
