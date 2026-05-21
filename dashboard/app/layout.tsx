import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Kindynos — Arbitrage Engine',
  description: 'Real-time cross-venue arbitrage detection dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#0a0a0a] text-gray-100 antialiased min-h-screen">
        {children}
      </body>
    </html>
  )
}
