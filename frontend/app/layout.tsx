import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Subnet Intelligence',
  description: 'Automated Bittensor Subnet Scoring for Investors',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-200 antialiased">
        <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
            <a href="/" className="text-lg font-bold text-green-400 tracking-tight">
              ⬡ Subnet Intelligence
            </a>
            <span className="text-xs text-slate-500">Bittensor · Public Beta</span>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
      </body>
    </html>
  )
}
