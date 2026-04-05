'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ReactNode } from 'react'

import { cn } from '@/lib/formatting'

const NAV_ITEMS = [
  { href: '/', label: 'Discover', match: (pathname: string) => pathname === '/' },
  { href: '/compare', label: 'Compare', match: (pathname: string) => pathname.startsWith('/compare') },
]

export default function AppShell({
  children,
  actions,
}: {
  children: ReactNode
  actions?: ReactNode
}) {
  const pathname = usePathname()

  return (
    <>
      <div className="fixed inset-0 -z-20 bg-[radial-gradient(circle_at_top,_rgba(34,197,94,0.08),_transparent_24%),radial-gradient(circle_at_80%_18%,_rgba(59,130,246,0.12),_transparent_26%),linear-gradient(180deg,_#071018,_#0a1219_42%,_#081017)]" />
      <div className="fixed inset-0 -z-10 bg-[linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:44px_44px] opacity-[0.08]" />
      <div className="min-h-screen">
        <header className="sticky top-0 z-50 border-b border-[color:var(--border-subtle)] bg-[color:rgba(7,16,24,0.88)] backdrop-blur-xl">
          <div className="mx-auto flex min-h-[72px] max-w-[1440px] items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
            <div className="min-w-0">
              <Link href="/" className="text-lg font-semibold tracking-tight text-[color:var(--text-primary)]">
                SubIntel
              </Link>
              <p className="text-[11px] tracking-[0.08em] text-[color:var(--text-tertiary)]">
                See what the market misses
              </p>
            </div>

            <div className="flex items-center gap-2">
              <nav className="flex max-w-full items-center gap-1 overflow-x-auto rounded-full border border-[color:var(--border-subtle)] bg-[color:var(--surface-1)] p-1">
                {NAV_ITEMS.map((item) => {
                  const active = item.match(pathname)
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        'shrink-0 rounded-full px-4 py-2 text-sm transition-colors',
                        active
                          ? 'bg-[color:var(--surface-2)] text-[color:var(--text-primary)] shadow-[var(--shadow-soft)]'
                          : 'text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)]',
                      )}
                    >
                      {item.label}
                    </Link>
                  )
                })}
              </nav>
              {actions}
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </>
  )
}
