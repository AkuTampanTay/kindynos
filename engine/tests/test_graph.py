import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from graph import CurrencyGraph
from models import Edge


def make_edge(src, tgt, rate, exchange="TestEx", fee=0.0):
    return Edge(source=src, target=tgt, exchange=exchange, rate=rate, fee=fee)


class TestCurrencyGraph:
    def test_empty_graph(self):
        g = CurrencyGraph()
        assert g.node_count == 0
        assert g.edge_count == 0
        assert g.get_edges() == []
        assert g.get_nodes() == []

    def test_upsert_adds_nodes_and_edge(self):
        g = CurrencyGraph()
        g.upsert_edge(make_edge("USD", "BTC", 0.000025))
        assert "USD" in g.get_nodes()
        assert "BTC" in g.get_nodes()
        assert g.edge_count == 1
        assert g.node_count == 2

    def test_upsert_same_key_updates_in_place(self):
        g = CurrencyGraph()
        g.upsert_edge(make_edge("USD", "BTC", 0.000025, exchange="Binance"))
        g.upsert_edge(make_edge("USD", "BTC", 0.000026, exchange="Binance"))
        assert g.edge_count == 1
        assert g.get_edges()[0].rate == 0.000026

    def test_different_exchanges_create_separate_edges(self):
        g = CurrencyGraph()
        g.upsert_edge(make_edge("USD", "BTC", 0.000025, exchange="Binance"))
        g.upsert_edge(make_edge("USD", "BTC", 0.000024, exchange="Bybit"))
        assert g.edge_count == 2
        assert g.node_count == 2  # still only 2 unique nodes

    def test_best_edge_returns_highest_rate(self):
        g = CurrencyGraph()
        g.upsert_edge(make_edge("USD", "BTC", 0.000024, exchange="Bybit"))
        g.upsert_edge(make_edge("USD", "BTC", 0.000025, exchange="Binance"))
        best = g.best_edge("USD", "BTC")
        assert best is not None
        assert best.rate == 0.000025
        assert best.exchange == "Binance"

    def test_best_edge_missing_returns_none(self):
        g = CurrencyGraph()
        assert g.best_edge("USD", "ETH") is None

    def test_remove_edge(self):
        g = CurrencyGraph()
        g.upsert_edge(make_edge("A", "B", 1.5, exchange="X"))
        g.remove_edge("A", "B", "X")
        assert g.edge_count == 0

    def test_remove_nonexistent_edge_is_noop(self):
        g = CurrencyGraph()
        g.remove_edge("A", "B", "X")  # should not raise

    def test_edge_weight_is_negative_log_effective_rate(self):
        import math
        fee = 0.001
        rate = 2.0
        edge = Edge(source="A", target="B", exchange="X", rate=rate, fee=fee)
        expected = -math.log(rate * (1 - fee))
        assert abs(edge.weight - expected) < 1e-12

    def test_edge_weight_zero_rate_is_inf(self):
        import math
        edge = Edge(source="A", target="B", exchange="X", rate=0.0)
        assert edge.weight == math.inf
