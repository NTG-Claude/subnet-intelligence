import CompareWorkspace from '@/features/compare/components/CompareWorkspace'
import { fetchCompareTimeseries } from '@/lib/api'

export const dynamic = 'force-dynamic'

export default async function ComparePage() {
  const data = await fetchCompareTimeseries(90)

  return <CompareWorkspace data={data} />
}
