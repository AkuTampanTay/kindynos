'use client'

import { useArbitrageStream } from '@/hooks/useArbitrageStream'
import { Header } from './Header'
import { RiskGrid } from './RiskGrid'
import { SignalFeed } from './SignalFeed'

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8765'

export function DashboardClient() {
  const { connected, signals, risk } = useArbitrageStream(WS_URL)

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <Header connected={connected} signalCount={signals.length} />

      <main className="flex flex-1 min-h-0 divide-x divide-[#1e1e1e]">
        {/* Left: Arbitrage signals (wider) */}
        <section className="flex flex-col flex-[3] min-w-0">
          <div className="px-5 py-3 border-b border-[#1e1e1e] shrink-0">
            <h2 className="font-mono text-[11px] uppercase tracking-widest text-gray-600">
              Arbitrage Signals
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <SignalFeed signals={signals} />
          </div>
        </section>

        {/* Right: Risk metrics (narrower) */}
        <section className="flex flex-col flex-[2] min-w-0">
          <div className="px-5 py-3 border-b border-[#1e1e1e] shrink-0">
            <h2 className="font-mono text-[11px] uppercase tracking-widest text-gray-600">
              Risk Metrics
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <RiskGrid snapshot={risk} />
          </div>
        </section>
      </main>
    </div>
  )
}
