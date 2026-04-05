import type { Metadata } from 'next'

import AppShell from '@/components/layout/AppShell'
import './globals.css'

export const metadata: Metadata = {
  title: 'SubIntel',
  description: 'See what the market misses.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[color:var(--bg)] text-[color:var(--text-primary)] antialiased">
        <AppShell>
          {children}
        </AppShell>
      </body>
    </html>
  )
}
