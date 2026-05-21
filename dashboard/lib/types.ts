export interface Leg {
  source: string
  target: string
  exchange: string
  rate: number
  fee: number
}

export interface Opportunity {
  cycle: string[]
  profit_ratio: number
  profit_pct: number
  timestamp_ms: number
  legs: Leg[]
}

export interface PairRisk {
  samples: number
  volatility: number | null
  var_95: number | null
}

export type RiskSnapshot = Record<string, PairRisk>

export type StreamEvent =
  | { type: 'opportunity'; data: Opportunity }
  | { type: 'risk'; data: RiskSnapshot }
