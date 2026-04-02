import { Skeleton } from '@/components/shared/research-ui'

export default function SubnetDetailLoading() {
  return (
    <div className="space-y-6 page-enter">
      {/* Breadcrumb */}
      <Skeleton className="h-4 w-48 rounded-lg" />

      {/* Header */}
      <div className="rounded-[2rem] border border-white/10 bg-[#10151b] p-5 sm:p-6">
        <div className="space-y-4">
          <div className="flex gap-2">
            <Skeleton className="h-6 w-16 rounded-full" />
            <Skeleton className="h-6 w-24 rounded-full" />
          </div>
          <Skeleton className="h-10 w-72" />
          <Skeleton className="h-5 w-full max-w-xl" />
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-2xl" />
            ))}
          </div>
        </div>
      </div>

      {/* Section nav */}
      <Skeleton className="h-10 rounded-xl" />

      {/* Content sections */}
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-48 rounded-3xl" style={{ animationDelay: `${i * 80}ms` }} />
      ))}
    </div>
  )
}
