import { ReactNode } from 'react'

import { cn } from '@/lib/formatting'

export interface HeaderStat {
  label: string
  value: string
  tone?: 'default' | 'warning' | 'success'
}

function statToneClass(tone?: HeaderStat['tone']): string {
  switch (tone) {
    case 'warning':
      return 'text-[color:var(--warning-strong)]'
    case 'success':
      return 'text-[color:var(--success-strong)]'
    default:
      return 'text-[color:var(--text-primary)]'
  }
}

export default function PageHeader({
  title,
  subtitle,
  stats,
  actions,
  variant = 'standard',
}: {
  title: string
  subtitle?: string
  stats?: HeaderStat[]
  actions?: ReactNode
  variant?: 'compact' | 'standard' | 'research'
}) {
  return (
    <section
      className={cn(
        'surface-panel overflow-hidden',
        variant === 'compact' ? 'p-4 sm:p-5' : 'p-5 sm:p-6',
        variant === 'research' ? 'lg:p-7' : '',
      )}
    >
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-4xl space-y-2">
          <p className="eyebrow">Subnet Intelligence</p>
          <h1 className={cn('font-semibold tracking-tight text-[color:var(--text-primary)]', variant === 'research' ? 'text-4xl sm:text-5xl' : 'text-3xl sm:text-4xl')}>
            {title}
          </h1>
          {subtitle ? <p className="max-w-3xl text-sm leading-6 text-[color:var(--text-secondary)] sm:text-base">{subtitle}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
      </div>

      {stats?.length ? (
        <div className="mt-6 grid gap-3 md:grid-cols-3">
          {stats.map((stat) => (
            <div key={stat.label} className="surface-subtle min-h-[92px] p-4">
              <div className="eyebrow">{stat.label}</div>
              <div className={cn('mt-3 text-xl font-semibold tracking-tight', statToneClass(stat.tone))}>{stat.value}</div>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  )
}
