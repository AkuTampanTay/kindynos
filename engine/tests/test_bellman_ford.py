import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from graph import CurrencyGraph
from bellman_ford import detect_arbitrage, _canonical_key
from models import Edge


def edge(src, tgt, rate, exchange="TestEx", fee=0.0):
    return Edge(source=src, target=tgt, exchange=exchange, rate=rate, fee=fee)


def build_graph(*edges):
    g = CurrencyGraph()
    for e in edges:
        g.upsert_edge(e)
    return g


class TestCanonicalKey:
    def test_rotates_to_min_node(self):
        assert _canonical_key(["B", "C", "A", "B"]) == ("A", "B", "C")

    def test_already_canonical(self):
        assert _canonical_key(["A", "B", "C", "A"]) == ("A", "B", "C")

    def test_single_node_cycle(self):
        assert _canonical_key(["Z", "Z"]) == ("Z",)


class TestDetectArbitrage:
    def test_empty_graph_returns_no_opportunities(self):
        g = CurrencyGraph()
        assert detect_arbitrage(g) == []

    def test_no_cycle_returns_empty(self):
        # A→B→C chain with no return path
        g = build_graph(
            edge("A", "B", 2.0),
            edge("B", "C", 2.0),
        )
        assert detect_arbitrage(g) == []

    def test_balanced_triangle_no_profit(self):
        # A→B→C→A with rates that yield exactly 1.0 (break-even)
        # 2.0 * 2.0 * 0.25 = 1.0 — not profitable
        g = build_graph(
            edge("A", "B", 2.0),
            edge("B", "C", 2.0),
            edge("C", "A", 0.25),
        )
        opps = detect_arbitrage(g)
        assert opps == []

    def test_triangle_with_profit_no_fees(self):
        # 2.0 * 2.0 * 0.3 = 1.2 → 20% profit with zero fees
        g = build_graph(
            edge("A", "B", 2.0),
            edge("B", "C", 2.0),
            edge("C", "A", 0.3),
        )
        opps = detect_arbitrage(g)
        assert len(opps) == 1
        opp = opps[0]
        assert abs(opp.profit_ratio - 1.2) < 1e-9
        assert opp.profit_pct > 0

    def test_triangle_with_realistic_fees_still_profitable(self):
        # Triangular: USD → BTC → ETH → USD
        # 0.000025 * 15 * 2800 = 1.05 (5% gross); fees 0.1% per leg
        # effective: 0.000025*0.999 * 15*0.999 * 2800*0.999 ≈ 1.0469
        g = build_graph(
            edge("USD", "BTC", 0.000025, fee=0.001),
            edge("BTC", "ETH", 15.0,     fee=0.001),
            edge("ETH", "USD", 2800.0,   fee=0.001),
        )
        opps = detect_arbitrage(g)
        assert len(opps) == 1
        assert opps[0].profit_ratio > 1.0
        assert opps[0].profit_pct > 4.5

    def test_triangle_fees_eliminate_marginal_profit(self):
        # 2.0 * 2.0 * 0.250 = 1.000 gross; (1-0.001)^3 ≈ 0.997 → net < 1.0
        # break-even rate for C→A is ~0.25075, so 0.250 is safely below it
        g = build_graph(
            edge("A", "B", 2.0,  fee=0.001),
            edge("B", "C", 2.0,  fee=0.001),
            edge("C", "A", 0.25, fee=0.001),
        )
        opps = detect_arbitrage(g)
        assert opps == []

    def test_same_cycle_deduplicated(self):
        # Running Bellman-Ford from each node can discover the same cycle;
        # results must be deduplicated by canonical key.
        g = build_graph(
            edge("A", "B", 2.0),
            edge("B", "C", 2.0),
            edge("C", "A", 0.3),
        )
        opps = detect_arbitrage(g)
        assert len(opps) == 1

    def test_cross_venue_best_rate_selected(self):
        # Binance offers 2.0, Bybit offers 2.1 for A→B.
        # Engine should use Bybit (higher rate) when building the opportunity.
        g = build_graph(
            edge("A", "B", 2.0,  exchange="Binance"),
            edge("A", "B", 2.1,  exchange="Bybit"),
            edge("B", "C", 2.0),
            edge("C", "A", 0.3),
        )
        opps = detect_arbitrage(g)
        assert len(opps) >= 1
        best = opps[0]
        a_to_b_leg = next(e for e in best.legs if e.source == "A" and e.target == "B")
        assert a_to_b_leg.exchange == "Bybit"

    def test_opportunities_sorted_by_descending_profit(self):
        # Two separate triangles with different profit margins.
        # Triangle 1: A→B→C→A  profit ~1.2
        # Triangle 2: D→E→F→D  profit ~1.5
        g = build_graph(
            edge("A", "B", 2.0),
            edge("B", "C", 2.0),
            edge("C", "A", 0.3),   # 2*2*0.3 = 1.2
            edge("D", "E", 3.0),
            edge("E", "F", 3.0),
            edge("F", "D", 1.0 / 6.0 * 1.5),  # 3*3*(1/6*1.5)=2.25 — wait let me recalc
        )
        # 3 * 3 * (1/(3*3)) * 1.5 = 1.5 — but 1/(3*3)=0.111 so 3*3*0.111*1.5 = 1.5
        opps = detect_arbitrage(g)
        for i in range(len(opps) - 1):
            assert opps[i].profit_ratio >= opps[i + 1].profit_ratio

    def test_result_cycle_closes_on_itself(self):
        g = build_graph(
            edge("USD", "BTC", 0.000025),
            edge("BTC", "ETH", 15.0),
            edge("ETH", "USD", 2800.0),
        )
        opps = detect_arbitrage(g)
        if opps:
            opp = opps[0]
            assert opp.cycle[0] == opp.cycle[-1]

    def test_single_pair_no_cycle(self):
        g = build_graph(edge("A", "B", 100.0))
        assert detect_arbitrage(g) == []
