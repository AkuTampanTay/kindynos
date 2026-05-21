import type { Opportunity } from '@/lib/types'

function formatAge(ms: number): string {
  const diff = Date.now() - ms
  if (diff < 1_000) return 'just now'
  if (diff < 60_000) return `${Math.floor(diff / 1_000)}s ago`
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`
  return `${Math.floor(diff / 3_600_000)}h ago`
}

function formatProfit(pct: number): string {
  return pct < 1 ? `+${pct.toFixed(4)}%` : `+${pct.toFixed(2)}%`
}

export function SignalFeed({ signals }: { signals: Opportunity[] }) {
  if (signals.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-52 text-center">
        <span className="w-2 h-2 bg-gray-700 rounded-full mb-4 animate-pulse" />
        <p className="text-gray-600 text-sm font-mono">Waiting for arbitrage signals…</p>
        <p className="text-gray-700 text-xs mt-1.5">
          Graph populates over the first few seconds of market data
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {signals.map((s, i) => (
        <SignalCard key={`${s.timestamp_ms}-${i}`} signal={s} />
      ))}
    </div>
  )
}

function SignalCard({ signal }: { signal: Opportunity }) {
  const cycle = signal.cycle.join(' → ')
  const exchanges = [...new Set(signal.legs.map((l) => l.exchange))].join(', ')

  return (
    <div className="bg-[#0d160d] border border-emerald-900/40 rounded-lg p-4 hover:border-emerald-700/50 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <span className="font-mono text-emerald-400 text-sm break-all leading-snug">
          {cycle}
        </span>
        <span className="font-bold text-emerald-300 shrink-0 tabular-nums">
          {formatProfit(signal.profit_pct)}
        </span>
      </div>

      <div className="flex items-center justify-between mt-1.5">
        <span className="text-gray-500 text-xs">{exchanges}</span>
        <span className="text-gray-600 text-xs tabular-nums">
          {formatAge(signal.timestamp_ms)}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {signal.legs.map((leg, i) => (
          <span
            key={i}
            className="font-mono text-xs text-gray-400 bg-[#111] border border-[#1e2e1e] px-2 py-1 rounded"
          >
            {leg.source}→{leg.target}
            <span className="text-gray-600 ml-1.5 tabular-nums">
              {leg.rate.toPrecision(6)}
            </span>
          </span>
        ))}
      </div>
    </div>
  )
}
