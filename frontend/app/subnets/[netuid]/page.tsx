import { notFound } from 'next/navigation'
import { fetchSubnet } from '@/lib/api'
import ScoreGauge from '@/components/ScoreGauge'
import SignalBreakdown from '@/components/SignalBreakdown'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'

interface Props {
  params: Promise<{ netuid: string }>
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    timeZone: 'UTC',
  })
}

function countSignals(breakdown: Record<string, number>): number {
  return Object.values(breakdown).filter((v) => v > 0).length
}

export default async function SubnetPage({ params }: Props) {
  const { netuid: netuidStr } = await params
  const netuid = parseInt(netuidStr, 10)
  if (isNaN(netuid)) notFound()

  let subnet
  try {
    subnet = await fetchSubnet(netuid)
  } catch {
    notFound()
  }

  const { breakdown, history, metadata } = subnet
  const signalsWithData = countSignals(breakdown as unknown as Record<string, number>)

  const chartData = history.map((h) => ({
    date: new Date(h.computed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    score: h.score,
  }))

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Back */}
      <a href="/" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200 transition-colors">
        ← All Subnets
      </a>

      {/* Header */}
      <div className="flex flex-col sm:flex-row gap-8 items-start sm:items-center">
        <ScoreGauge score={subnet.score} signalsWithData={signalsWithData} />

        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-100">
              {subnet.name ?? `Subnet ${netuid}`}
            </h1>
            <span className="text-xs font-mono bg-slate-800 border border-slate-700 rounded px-2 py-0.5 text-slate-400">
              SN{netuid}
            </span>
          </div>

          <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-400">
            {subnet.rank && <span>Rank <strong className="text-slate-200">#{subnet.rank}</strong></span>}
            {subnet.percentile != null && (
              <span>Top <strong className="text-slate-200">{(100 - subnet.percentile).toFixed(0)}%</strong></span>
            )}
            {subnet.computed_at && (
              <span>Updated <strong className="text-slate-200">{formatDate(subnet.computed_at)}</strong></span>
            )}
          </div>

          {/* External links */}
          <div className="flex flex-wrap gap-3 pt-1">
            <a
              href={`https://taostats.io/subnet/${netuid}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              Taostats ↗
            </a>
            {metadata?.github_url && (
              <a
                href={metadata.github_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              >
                GitHub ↗
              </a>
            )}
            {metadata?.website && (
              <a
                href={metadata.website}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              >
                Website ↗
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Score breakdown */}
      <section className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-5">
          Score Breakdown
        </h2>
        <SignalBreakdown breakdown={breakdown} />
      </section>

      {/* History chart */}
      {chartData.length > 1 && (
        <section className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-5">
            Score History (30 days)
          </h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: '#64748b' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 11, fill: '#64748b' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
                formatter={(v: number) => [v.toFixed(1), 'Score']}
              />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#4ade80"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#4ade80' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* Score methodology note */}
      <section className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 text-xs text-slate-500 leading-relaxed space-y-1">
        <p className="font-semibold text-slate-400">Score Methodology v{subnet.score_version}</p>
        <p>
          Composite = Capital(25) + Activity(25) + Efficiency(20) + Health(15) + Dev(15).
          Each signal is percentile-ranked across all active subnets.
          Missing data is scored pessimistically (0).
        </p>
        <p>
          Data sources: Taostats API · GitHub API. Updated daily at 06:00 UTC.
          This is not financial advice.
        </p>
      </section>
    </div>
  )
}
