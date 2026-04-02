import DiscoverWorkspace from '@/features/discover/components/DiscoverWorkspace'
import { fetchLatestRun, fetchSubnets } from '@/lib/api'

export const dynamic = 'force-dynamic'

export default async function HomePage() {
  const [{ subnets }, latest] = await Promise.all([
    fetchSubnets(200).catch(() => ({ subnets: [], total: 0 })),
    fetchLatestRun().catch(() => ({ last_score_run: null, subnet_count: 0 })),
  ])

  const scored = subnets.filter((subnet) => subnet.primary_outputs)
  const lowConfidenceCount = scored.filter((subnet) => (subnet.primary_outputs?.signal_confidence ?? 0) < 50).length
  const awaitingRunCount = subnets.length - scored.length

  return (
    <DiscoverWorkspace
      subnets={subnets}
      lastRun={latest.last_score_run}
      trackedUniverse={latest.subnet_count || subnets.length}
      awaitingRunCount={awaitingRunCount}
      lowConfidenceCount={lowConfidenceCount}
    />
  )
}
