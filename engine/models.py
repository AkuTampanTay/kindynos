import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class SignalStatus(Enum):
    CONFIRMED = "confirmed"
    UNCONFIRMED = "unconfirmed"
    EXPIRED = "expired"


@dataclass
class Edge:
    source: str
    target: str
    exchange: str
    rate: float
    fee: float = 0.001  # 0.1% taker fee baseline

    # Derived — set automatically after init
    weight: float = field(init=False)

    def __post_init__(self):
        effective_rate = self.rate * (1.0 - self.fee)
        self.weight = -math.log(effective_rate) if effective_rate > 0 else math.inf

    def __repr__(self):
        return f"Edge({self.source}->{self.target} @ {self.exchange}, rate={self.rate}, fee={self.fee})"


@dataclass
class ArbitrageOpportunity:
    cycle: List[str]        # e.g. ["USD", "BTC", "ETH", "USD"]
    profit_ratio: float     # e.g. 1.0023 = 0.23% profit after fees
    legs: List[Edge]
    status: SignalStatus = SignalStatus.CONFIRMED
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    @property
    def profit_pct(self) -> float:
        return (self.profit_ratio - 1.0) * 100.0

    def __repr__(self):
        path = " → ".join(self.cycle)
        return f"ArbitrageOpportunity({path}, +{self.profit_pct:.4f}%)"
