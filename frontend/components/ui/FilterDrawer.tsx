'use client'

import { ReactNode } from 'react'

import { cn } from '@/lib/formatting'

export default function FilterDrawer({
  title,
  subtitle,
  open,
  onToggle,
  children,
}: {
  title: string
  subtitle?: string
  open: boolean
  onToggle: () => void
  children: ReactNode
}) {
  return (
    <section className="surface-panel p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="section-title">{title}</div>
          {subtitle ? <p className="mt-1 text-sm text-[color:var(--text-secondary)]">{subtitle}</p> : null}
        </div>
        <button type="button" onClick={onToggle} className="button-secondary">
          {open ? 'Hide filters' : 'Show filters'}
        </button>
      </div>

      <div
        className={cn(
          'grid transition-[grid-template-rows,opacity,margin] duration-200',
          open ? 'mt-4 grid-rows-[1fr] opacity-100' : 'mt-0 grid-rows-[0fr] opacity-0',
        )}
      >
        <div className="overflow-hidden">{children}</div>
      </div>
    </section>
  )
}
