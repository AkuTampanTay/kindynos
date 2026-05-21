import asyncio
import json
import logging
from typing import Awaitable, Callable, Dict, Optional

from aiokafka import AIOKafkaConsumer

from bellman_ford import detect_arbitrage
from graph import CurrencyGraph
from models import ArbitrageOpportunity, Edge
from redis_store import RedisStore
from risk import RiskEngine
from risk_filter import RiskFilter

logger = logging.getLogger(__name__)

OpportunityCallback = Callable[[ArbitrageOpportunity], Awaitable[None]]
RiskSnapshotCallback = Callable[[Dict], Awaitable[None]]


class MarketDataConsumer:
    """
    Consumes normalised market-data events from Kafka, maintains the live
    CurrencyGraph and in-memory RiskEngine, and runs two background loops:

    _ingest_loop     — updates graph + risk on every Kafka message (hot path,
                       no I/O beyond the queue read)
    _detection_loop  — runs Bellman-Ford every `detection_interval_ms` ms,
                       filters signals through RiskFilter, fires callback
    _risk_loop       — every `risk_snapshot_interval_s` seconds, persists risk
                       metrics to Redis and fires the risk snapshot callback
    """

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str = "arbitrage-engine",
        detection_interval_ms: int = 100,
        risk_snapshot_interval_s: int = 5,
        redis_store: Optional[RedisStore] = None,
        on_opportunity: Optional[OpportunityCallback] = None,
        on_risk_snapshot: Optional[RiskSnapshotCallback] = None,
    ):
        self.graph = CurrencyGraph()
        self.risk = RiskEngine()
        self._risk_filter = RiskFilter(self.risk)
        self._bootstrap = bootstrap_servers
        self._topic = topic
        self._group_id = group_id
        self._detection_interval = detection_interval_ms / 1000.0
        self._risk_interval = risk_snapshot_interval_s
        self._redis_store = redis_store
        self._on_opportunity = on_opportunity
        self._on_risk_snapshot = on_risk_snapshot
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
        self._graph_dirty = False

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap,
            group_id=self._group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._running = True
        logger.info(f"Engine consumer subscribed to '{self._topic}' @ {self._bootstrap}")

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            logger.info("Engine consumer stopped.")

    async def run(self) -> None:
        await self.start()
        try:
            await asyncio.gather(
                self._ingest_loop(),
                self._detection_loop(),
                self._risk_loop(),
            )
        finally:
            await self.stop()

    # ------------------------------------------------------------------
    # Internal loops
    # ------------------------------------------------------------------

    async def _ingest_loop(self) -> None:
        assert self._consumer is not None
        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                self._update_graph(msg.value)
                self._update_risk(msg.value)
        except asyncio.CancelledError:
            pass

    async def _detection_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._detection_interval)
            if not self._graph_dirty:
                continue
            self._graph_dirty = False

            opportunities = detect_arbitrage(self.graph)
            for opp in opportunities:
                if not self._risk_filter.is_viable(opp):
                    logger.debug(f"Signal filtered by VaR: {opp}")
                    continue
                logger.info(f"SIGNAL  {opp}")
                if self._on_opportunity:
                    try:
                        await self._on_opportunity(opp)
                    except Exception:
                        logger.exception("on_opportunity callback raised")

    async def _risk_loop(self) -> None:
        """
        Runs every `risk_snapshot_interval_s` seconds.
        Persists per-pair volatility and VaR to Redis and fires the snapshot
        callback so the publisher can forward it to the dashboard.
        """
        while self._running:
            await asyncio.sleep(self._risk_interval)
            snapshot = self.risk.snapshot()
            if not snapshot:
                continue

            if self._redis_store:
                for pair, metrics in snapshot.items():
                    await self._redis_store.store_risk_metrics(pair, metrics)

            # Graph state — lets you confirm multi-exchange edges are building
            nodes = self.graph.get_nodes()
            logger.info(
                f"Graph  {self.graph.node_count} nodes  {self.graph.edge_count} edges"
                f"  assets={nodes}  risk_pairs={len(snapshot)}"
            )

            if self._on_risk_snapshot:
                try:
                    await self._on_risk_snapshot(snapshot)
                except Exception:
                    logger.exception("on_risk_snapshot callback raised")

    # ------------------------------------------------------------------
    # Graph + risk updates (synchronous — no I/O)
    # ------------------------------------------------------------------

    def _update_graph(self, data: dict) -> None:
        base = data["base"]
        quote = data["quote"]
        exchange = data["exchange"]
        bid = float(data["bid"])
        ask = float(data["ask"])

        if bid > 0:
            self.graph.upsert_edge(
                Edge(source=base, target=quote, exchange=exchange, rate=bid)
            )
        if ask > 0:
            self.graph.upsert_edge(
                Edge(source=quote, target=base, exchange=exchange, rate=1.0 / ask)
            )
        self._graph_dirty = True

    def _update_risk(self, data: dict) -> None:
        mid = (float(data["bid"]) + float(data["ask"])) / 2.0
        pair = f"{data['exchange']}:{data['base']}/{data['quote']}"
        self.risk.update(pair, mid)
