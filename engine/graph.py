from typing import Dict, List, Optional, Tuple

from models import Edge


class CurrencyGraph:
    """
    In-memory directed graph where nodes are assets and edges are trading pairs.
    Edge weights are -log(rate * (1 - fee)) so that a negative-weight cycle
    corresponds to a profitable arbitrage loop.
    """

    def __init__(self):
        self._edges: Dict[Tuple[str, str, str], Edge] = {}
        self._nodes: set = set()

    def upsert_edge(self, edge: Edge) -> None:
        key = (edge.source, edge.target, edge.exchange)
        self._edges[key] = edge
        self._nodes.add(edge.source)
        self._nodes.add(edge.target)

    def remove_edge(self, source: str, target: str, exchange: str) -> None:
        key = (source, target, exchange)
        self._edges.pop(key, None)

    def get_edges(self) -> List[Edge]:
        return list(self._edges.values())

    def get_nodes(self) -> List[str]:
        return sorted(self._nodes)

    def get_edges_from(self, source: str) -> List[Edge]:
        return [e for e in self._edges.values() if e.source == source]

    def best_edge(self, source: str, target: str) -> Optional[Edge]:
        candidates = [
            e for e in self._edges.values()
            if e.source == source and e.target == target
        ]
        return max(candidates, key=lambda e: e.rate) if candidates else None

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def __repr__(self):
        return f"CurrencyGraph(nodes={self.node_count}, edges={self.edge_count})"
