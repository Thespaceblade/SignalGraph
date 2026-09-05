"""Lightweight market relationship graph representation.

NetworkX is optional later; this module uses a simple adjacency structure so
core research workflows do not require an extra dependency.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from signalgraph.relationships.grouping import MarketGroup, MarketRef


def _node_id(ref: MarketRef) -> str:
    return f"{ref.platform}:{ref.market_id}"


@dataclass
class MarketGraph:
    """Undirected multigraph of related markets keyed by platform:market_id."""

    nodes: set[str] = field(default_factory=set)
    edges: list[tuple[str, str, str]] = field(default_factory=list)
    # edge tuple: (source, target, relationship_type)
    adjacency: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    group_names: dict[str, str] = field(default_factory=dict)

    def add_group(self, group: MarketGroup) -> None:
        refs = group.real_market_refs()
        node_ids = [_node_id(r) for r in refs]
        for nid, ref in zip(node_ids, refs, strict=True):
            self.nodes.add(nid)
            self.group_names[nid] = group.name

        if group.relationship_type == "aggregate_constituent" and group.aggregate:
            agg = _node_id(group.aggregate)
            if group.aggregate.market_id.upper().startswith("REPLACE_WITH"):
                return
            for ref in group.constituents:
                if ref.market_id.upper().startswith("REPLACE_WITH"):
                    continue
                child = _node_id(ref)
                self._add_edge(agg, child, group.relationship_type)
        else:
            # Fully connect constituents for non-aggregate relationship types.
            for i, a in enumerate(node_ids):
                for b in node_ids[i + 1 :]:
                    self._add_edge(a, b, group.relationship_type)

    def _add_edge(self, a: str, b: str, relationship_type: str) -> None:
        self.nodes.add(a)
        self.nodes.add(b)
        self.edges.append((a, b, relationship_type))
        self.adjacency[a].add(b)
        self.adjacency[b].add(a)

    @classmethod
    def from_groups(cls, groups: dict[str, MarketGroup]) -> MarketGraph:
        graph = cls()
        for group in groups.values():
            graph.add_group(group)
        return graph

    def neighbors(self, node: str) -> set[str]:
        return set(self.adjacency.get(node, set()))
