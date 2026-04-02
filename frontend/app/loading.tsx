import { Skeleton } from '@/components/shared/research-ui'

export default function HomeLoading() {
  return (
    <div className="space-y-4 page-enter">
      {/* Header skeleton */}
      <div className="rounded-[1.6rem] border border-white/10 bg-[#10151b] p-5">
        <div className="space-y-3">
          <div className="flex gap-2">
            <Skeleton className="h-6 w-32 rounded-full" />
            <Skeleton className="h-6 w-20 rounded-full" />
          </div>
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96 max-w-full" />
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-2xl" />
          ))}
        </div>
      </div>

      {/* Toolbar skeleton */}
      <Skeleton className="h-12 rounded-2xl" />

      {/* Row skeletons */}
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-2xl" style={{ animationDelay: `${i * 60}ms` }} />
        ))}
      </div>
    </div>
  )
}
