"""
Tests for MarketDataConsumer graph-update logic.

We test _update_graph and _update_risk directly (no Kafka needed) because
the integration with Kafka is exercised by the ingestion pipeline e2e test.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from consumer import MarketDataConsumer


def make_consumer():
    return MarketDataConsumer(
        bootstrap_servers="localhost:9092",
        topic="market-data",
    )


def tick(base, quote, bid, ask, exchange="TestEx"):
    return {
        "exchange": exchange,
        "base": base,
        "quote": quote,
        "bid": bid,
        "ask": ask,
        "exchange_timestamp": 0,
        "ingest_timestamp": 1,
    }


class TestGraphUpdates:
    def test_tick_creates_two_directed_edges(self):
        c = make_consumer()
        c._update_graph(tick("BTC", "USDT", bid=40000.0, ask=40100.0))
        edges = {(e.source, e.target): e for e in c.graph.get_edges()}
        assert ("BTC", "USDT") in edges
        assert ("USDT", "BTC") in edges

    def test_bid_edge_rate_equals_bid(self):
        c = make_consumer()
        c._update_graph(tick("BTC", "USDT", bid=40000.0, ask=40100.0))
        edges = {(e.source, e.target): e for e in c.graph.get_edges()}
        assert edges[("BTC", "USDT")].rate == 40000.0

    def test_ask_edge_rate_is_inverse_of_ask(self):
        c = make_consumer()
        c._update_graph(tick("BTC", "USDT", bid=40000.0, ask=40100.0))
        edges = {(e.source, e.target): e for e in c.graph.get_edges()}
        expected = 1.0 / 40100.0
        assert abs(edges[("USDT", "BTC")].rate - expected) < 1e-12

    def test_subsequent_tick_updates_rate_in_place(self):
        c = make_consumer()
        c._update_graph(tick("BTC", "USDT", bid=40000.0, ask=40100.0))
        c._update_graph(tick("BTC", "USDT", bid=41000.0, ask=41100.0))
        edges = {(e.source, e.target): e for e in c.graph.get_edges()}
        assert edges[("BTC", "USDT")].rate == 41000.0

    def test_zero_bid_skips_edge(self):
        c = make_consumer()
        c._update_graph(tick("BTC", "USDT", bid=0.0, ask=40100.0))
        edges = {(e.source, e.target) for e in c.graph.get_edges()}
        assert ("BTC", "USDT") not in edges
        assert ("USDT", "BTC") in edges  # ask edge still created

    def test_zero_ask_skips_edge(self):
        c = make_consumer()
        c._update_graph(tick("BTC", "USDT", bid=40000.0, ask=0.0))
        edges = {(e.source, e.target) for e in c.graph.get_edges()}
        assert ("BTC", "USDT") in edges
        assert ("USDT", "BTC") not in edges

    def test_multi_exchange_same_pair_creates_separate_edges(self):
        c = make_consumer()
        c._update_graph(tick("ETH", "USDT", bid=2500.0, ask=2501.0, exchange="Binance"))
        c._update_graph(tick("ETH", "USDT", bid=2499.0, ask=2500.0, exchange="Bybit"))
        assert c.graph.edge_count == 4  # 2 directions × 2 exchanges

    def test_graph_dirty_flag_set_after_update(self):
        c = make_consumer()
        assert not c._graph_dirty
        c._update_graph(tick("BTC", "USDT", bid=40000.0, ask=40100.0))
        assert c._graph_dirty


class TestRiskUpdates:
    def test_risk_engine_receives_mid_price(self):
        c = make_consumer()
        c._update_risk(tick("BTC", "USDT", bid=40000.0, ask=40100.0))
        snap = c.risk.snapshot()
        assert "TestEx:BTC/USDT" in snap

    def test_volatility_available_after_sufficient_samples(self):
        c = make_consumer()
        import random
        base_price = 40000.0
        for i in range(30):
            p = base_price * (1 + random.uniform(-0.01, 0.01))
            c._update_risk(tick("BTC", "USDT", bid=p - 10, ask=p + 10))
        snap = c.risk.snapshot()
        assert snap["TestEx:BTC/USDT"]["volatility"] is not None
