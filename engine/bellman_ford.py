import time
from typing import Dict, List, Optional, Set, Tuple

from graph import CurrencyGraph
from models import ArbitrageOpportunity, Edge, SignalStatus


def detect_arbitrage(graph: CurrencyGraph) -> List[ArbitrageOpportunity]:
    """
    Run Bellman-Ford from every node to find all negative-weight cycles.

    A negative cycle in the -log(rate*(1-fee)) weight space means the product
    of effective rates around the loop exceeds 1.0 — a profitable arbitrage.

    Returns deduplicated, confirmed ArbitrageOpportunity instances sorted by
    descending profit ratio.
    """
    nodes = graph.get_nodes()
    edges = graph.get_edges()
    n = len(nodes)

    if n < 2 or not edges:
        return []

    node_index: Dict[str, int] = {node: i for i, node in enumerate(nodes)}
    opportunities: List[ArbitrageOpportunity] = []
    seen_cycles: Set[Tuple[str, ...]] = set()

    for source in nodes:
        dist = [float("inf")] * n
        pred = [-1] * n
        dist[node_index[source]] = 0.0

        # Relax n-1 times (standard Bellman-Ford)
        for _ in range(n - 1):
            updated = False
            for edge in edges:
                u = node_index[edge.source]
                v = node_index[edge.target]
                if dist[u] < float("inf") and dist[u] + edge.weight < dist[v]:
                    dist[v] = dist[u] + edge.weight
                    pred[v] = u
                    updated = True
            if not updated:
                break  # converged early

        # n-th relaxation pass — any further improvement reveals a negative cycle
        for edge in edges:
            u = node_index[edge.source]
            v = node_index[edge.target]
            if dist[u] < float("inf") and dist[u] + edge.weight < dist[v]:
                cycle_path = _extract_cycle(pred, v, n, nodes)
                if cycle_path is None:
                    continue
                canonical = _canonical_key(cycle_path)
                if canonical in seen_cycles:
                    continue
                seen_cycles.add(canonical)
                opp = _build_opportunity(cycle_path, edges)
                if opp is not None:
                    opportunities.append(opp)

    opportunities.sort(key=lambda o: o.profit_ratio, reverse=True)
    return opportunities


def _extract_cycle(
    pred: List[int], start: int, n: int, nodes: List[str]
) -> Optional[List[str]]:
    """
    Trace the predecessor chain to extract an actual negative-weight cycle.

    Walk n steps back first to guarantee we land inside the cycle (not just
    on a path leading into it), then collect the circuit until we revisit
    the anchor node.
    """
    x = start
    for _ in range(n):
        nxt = pred[x]
        if nxt == -1:
            return None
        x = nxt

    anchor = x
    path_indices: List[int] = [anchor]
    curr = pred[anchor]

    while curr != anchor:
        if curr == -1 or len(path_indices) > n:
            return None
        path_indices.append(curr)
        curr = pred[curr]

    path_indices.append(anchor)  # close the loop
    path_indices.reverse()
    return [nodes[i] for i in path_indices]


def _canonical_key(cycle: List[str]) -> Tuple[str, ...]:
    """
    Rotate the cycle so the lexicographically smallest node is first,
    enabling deduplication across runs that enter the same cycle at different
    points.
    """
    body = cycle[:-1]  # drop the repeated closing node
    min_idx = body.index(min(body))
    return tuple(body[min_idx:] + body[:min_idx])


def _build_opportunity(
    cycle: List[str], edges: List[Edge]
) -> Optional[ArbitrageOpportunity]:
    """
    Map a cycle path back to Edge objects and compute the net profit ratio.
    Picks the best rate across exchanges for each leg.
    Returns None if any leg is missing or net ratio ≤ 1.0.
    """
    cycle_edges: List[Edge] = []
    profit_ratio = 1.0

    for i in range(len(cycle) - 1):
        src, tgt = cycle[i], cycle[i + 1]
        best: Optional[Edge] = None
        for edge in edges:
            if edge.source == src and edge.target == tgt:
                if best is None or edge.rate > best.rate:
                    best = edge
        if best is None:
            return None
        cycle_edges.append(best)
        profit_ratio *= best.rate * (1.0 - best.fee)

    if profit_ratio <= 1.0:
        return None

    return ArbitrageOpportunity(
        cycle=cycle,
        profit_ratio=profit_ratio,
        legs=cycle_edges,
        status=SignalStatus.CONFIRMED,
        timestamp_ms=int(time.time() * 1000),
    )
