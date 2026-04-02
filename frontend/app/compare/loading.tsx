import { Skeleton } from '@/components/shared/research-ui'

export default function CompareLoading() {
  return (
    <div className="space-y-6 page-enter">
      <div className="space-y-3">
        <Skeleton className="h-4 w-32 rounded-lg" />
        <Skeleton className="h-4 w-16 rounded-lg" />
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <Skeleton key={i} className="h-96 rounded-3xl" style={{ animationDelay: `${i * 100}ms` }} />
        ))}
      </div>
    </div>
  )
}
