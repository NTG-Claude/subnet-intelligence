import { notFound } from 'next/navigation'

import SubnetResearchMemo from '@/components/subnet-detail/SubnetResearchMemo'
import { fetchSubnet } from '@/lib/api'
import { buildDetailMemo } from '@/lib/view-models/research'

export const dynamic = 'force-dynamic'

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

  return <SubnetResearchMemo memo={buildDetailMemo(subnet)} />
}
