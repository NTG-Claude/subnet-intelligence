import type { Metadata } from 'next'

import './globals.css'

export const metadata: Metadata = {
  title: 'Subnet Intelligence',
  description: 'Signal-separated Bittensor subnet research for earned strength, reflexivity, and fragility.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-stone-950 text-stone-100 antialiased">
        <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_top,_rgba(163,230,53,0.10),_transparent_22%),radial-gradient(circle_at_bottom_right,_rgba(251,191,36,0.10),_transparent_28%),linear-gradient(180deg,_#09090b,_#0c0a09_50%,_#09090b)]" />
        <header className="sticky top-0 z-50 border-b border-white/10 bg-stone-950/80 backdrop-blur-xl">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
            <a href="/" className="text-lg font-semibold tracking-tight text-stone-50">
              Subnet Intelligence
            </a>
            <div className="flex items-center gap-3 text-xs uppercase tracking-[0.24em] text-stone-500">
              <span className="rounded-full border border-lime-300/20 bg-lime-200/10 px-2.5 py-1 text-lime-100">Beta</span>
              <span>Bittensor Research</span>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">{children}</main>
      </body>
    </html>
  )
}
