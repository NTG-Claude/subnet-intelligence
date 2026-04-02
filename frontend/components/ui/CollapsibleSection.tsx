import { ReactNode } from 'react'

import { cn } from '@/lib/formatting'

export default function CollapsibleSection({
  title,
  subtitle,
  defaultOpen = true,
  children,
}: {
  title: string
  subtitle?: string
  defaultOpen?: boolean
  children: ReactNode
}) {
  return (
    <details open={defaultOpen} className="surface-panel group">
      <summary className="flex cursor-pointer list-none items-start justify-between gap-4 p-5 sm:p-6">
        <div>
          <div className="section-title">{title}</div>
          {subtitle ? <p className="mt-1 text-sm leading-6 text-[color:var(--text-secondary)]">{subtitle}</p> : null}
        </div>
        <span className="text-xs uppercase tracking-[0.2em] text-[color:var(--text-tertiary)] group-open:hidden">Expand</span>
        <span className="hidden text-xs uppercase tracking-[0.2em] text-[color:var(--text-tertiary)] group-open:block">Collapse</span>
      </summary>
      <div className={cn('border-t border-[color:var(--border-subtle)] px-5 pb-5 pt-5 sm:px-6 sm:pb-6')}>{children}</div>
    </details>
  )
}
