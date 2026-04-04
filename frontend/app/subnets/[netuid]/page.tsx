import { notFound } from 'next/navigation'

import ResearchWorkspace from '@/features/research/components/ResearchWorkspace'
import { fetchCompareTimeseries, fetchSubnet } from '@/lib/api'
import { buildDetailMemo } from '@/lib/view-models/research'

interface Props {
  params: Promise<{ netuid: string }>
}

export default async function SubnetPage({ params }: Props) {
  const { netuid: netuidStr } = await params
  const netuid = Number.parseInt(netuidStr, 10)
  if (Number.isNaN(netuid)) notFound()

  let subnet
  let compareTimeseries = null
  try {
    ;[subnet, compareTimeseries] = await Promise.all([
      fetchSubnet(netuid),
      fetchCompareTimeseries(45).catch(() => null),
    ])
  } catch {
    notFound()
  }

  const signalTrend =
    compareTimeseries?.runs
      .map((run) => {
        const point = run.subnets.find((item) => item.netuid === netuid)
        if (!point) return null
      return {
        computed_at: run.computed_at,
        score: point.score,
        quality: point.fundamental_quality,
        opportunity: point.mispricing_signal,
        risk: point.fragility_risk,
        confidence: point.signal_confidence,
      }
    })
      .filter((point): point is NonNullable<typeof point> => Boolean(point)) ?? []

  return <ResearchWorkspace memo={buildDetailMemo(subnet)} signalTrend={signalTrend} />
}
