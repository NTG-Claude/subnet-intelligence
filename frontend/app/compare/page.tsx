import CompareGrid from '@/components/compare/CompareGrid'
import { fetchSubnet } from '@/lib/api'
import { buildDetailMemo } from '@/lib/view-models/research'

export const dynamic = 'force-dynamic'

interface Props {
  searchParams?: Promise<{ ids?: string }>
}

export default async function ComparePage({ searchParams }: Props) {
  const params = (await searchParams) ?? {}
  const ids = (params.ids ?? '')
    .split(',')
    .map((value) => Number.parseInt(value, 10))
    .filter((value, index, all) => Number.isFinite(value) && all.indexOf(value) === index)
    .slice(0, 4)

  const subnets = await Promise.all(ids.map((id) => fetchSubnet(id).catch(() => null)))
  const memos = subnets.flatMap((item) => (item ? [buildDetailMemo(item)] : []))

  if (!memos.length) {
    return (
      <div className="rounded-[2rem] border border-dashed border-white/10 bg-black/20 p-10 text-center">
        <div className="text-[11px] uppercase tracking-[0.24em] text-stone-500">Compare</div>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-50">No subnets selected</h1>
        <p className="mt-2 text-sm leading-6 text-stone-400">
          Add two to four names from the ranking list to compare thesis, support, risks, confidence, and execution side by side.
        </p>
      </div>
    )
  }

  return <CompareGrid memos={memos} />
}
