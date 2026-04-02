import type { Metadata } from 'next'
import Link from 'next/link'

import './globals.css'

export const metadata: Metadata = {
  title: 'Subnet Intelligence',
  description: 'V2-first subnet research terminal for signal screening, thesis review, confidence, and conditioning.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-stone-950 text-stone-100 antialiased">
        <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.04),_transparent_18%),linear-gradient(180deg,_#0a0d11,_#0b1116_52%,_#0a0d11)]" />
        <div className="fixed inset-0 -z-10 opacity-[0.08] [background-image:linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] [background-size:36px_36px]" />
        <header className="sticky top-0 z-50 border-b border-white/10 bg-stone-950/90 backdrop-blur-xl">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
            <Link href="/" className="text-lg font-semibold tracking-tight text-stone-50">
              Subnet Intelligence
            </Link>
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.24em] text-stone-500">
              <Link href="/" className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-stone-300 transition-colors hover:bg-white/[0.08]">
                Universe
              </Link>
              <Link href="/compare" className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-stone-300 transition-colors hover:bg-white/[0.08]">
                Compare
              </Link>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </body>
    </html>
  )
}
