import type { PairRisk, RiskSnapshot } from '@/lib/types'

export function RiskGrid({ snapshot }: { snapshot: RiskSnapshot }) {
  const entries = Object.entries(snapshot)

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-52 text-center">
        <span className="w-2 h-2 bg-gray-700 rounded-full mb-4 animate-pulse" />
        <p className="text-gray-600 text-sm font-mono">Collecting risk data…</p>
        <p className="text-gray-700 text-xs mt-1.5">
          VaR needs ~10 price samples per pair (~5–10s)
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {entries.map(([pair, metrics]) => (
        <RiskCard key={pair} pair={pair} metrics={metrics} />
      ))}
    </div>
  )
}

function RiskCard({ pair, metrics }: { pair: string; metrics: PairRisk }) {
  const colonIdx = pair.indexOf(':')
  const exchange = colonIdx >= 0 ? pair.slice(0, colonIdx) : '—'
  const symbol   = colonIdx >= 0 ? pair.slice(colonIdx + 1) : pair

  const vol = metrics.volatility != null
    ? `${(metrics.volatility * 100).toFixed(2)}%`
    : '—'

  const var95 = metrics.var_95 != null
    ? `${(metrics.var_95 * 100).toFixed(3)}%`
    : '—'

  const volColor =
    metrics.volatility == null  ? 'text-gray-500'
    : metrics.volatility > 0.8 ? 'text-red-400'
    : metrics.volatility > 0.4 ? 'text-orange-400'
    :                             'text-yellow-300'

  const varColor =
    metrics.var_95 == null    ? 'text-gray-500'
    : metrics.var_95 < -0.02  ? 'text-red-400'
    :                            'text-yellow-400'

  return (
    <div className="bg-[#111] border border-[#1e1e1e] rounded-lg p-3 hover:border-[#2a2a2a] transition-colors">
      <div className="flex items-center justify-between mb-3">
        <span className="font-mono text-sm text-gray-200">{symbol}</span>
        <span className="text-xs text-gray-600 bg-[#1a1a1a] px-2 py-0.5 rounded border border-[#222]">
          {exchange}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Volatility</div>
          <div className={`font-mono text-sm tabular-nums ${volColor}`}>{vol}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">VaR 95%</div>
          <div className={`font-mono text-sm tabular-nums ${varColor}`}>{var95}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Samples</div>
          <div className="font-mono text-sm tabular-nums text-gray-400">{metrics.samples}</div>
        </div>
      </div>
    </div>
  )
}
