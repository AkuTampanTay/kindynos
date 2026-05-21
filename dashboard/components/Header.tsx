interface HeaderProps {
  connected: boolean
  signalCount: number
}

export function Header({ connected, signalCount }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-[#1e1e1e] shrink-0">
      <div className="flex items-center gap-3">
        <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.7)]" />
        <h1 className="font-mono text-base font-semibold tracking-tight">
          KINDYNOS
          <span className="text-gray-600 ml-2 text-sm font-normal">/ arbitrage engine</span>
        </h1>
      </div>

      <div className="flex items-center gap-5">
        <span className="font-mono text-xs text-gray-600">
          {signalCount} signal{signalCount !== 1 ? 's' : ''} detected
        </span>
        <div
          className={`flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded border transition-colors ${
            connected
              ? 'text-emerald-400 border-emerald-800/60 bg-emerald-950/30'
              : 'text-gray-600 border-[#222] bg-[#111]'
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              connected ? 'bg-emerald-400 animate-pulse' : 'bg-gray-600'
            }`}
          />
          {connected ? 'CONNECTED' : 'RECONNECTING…'}
        </div>
      </div>
    </header>
  )
}
