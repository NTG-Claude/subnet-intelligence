import { notFound } from 'next/navigation'

import ResearchWorkspace from '@/features/research/components/ResearchWorkspace'
import { fetchSubnet } from '@/lib/api'
import { buildDetailMemo } from '@/lib/view-models/research'

interface Props {
  params: Promise<{ netuid: string }>
}

export default async function SubnetPage({ params }: Props) {
  const { netuid: netuidStr } = await params
  const netuid = Number.parseInt(netuidStr, 10)
  if (Number.isNaN(netuid)) notFound()

  let subnet
  try {
    subnet = await fetchSubnet(netuid)
  } catch {
    notFound()
  }

  return <ResearchWorkspace memo={buildDetailMemo(subnet)} />
}
