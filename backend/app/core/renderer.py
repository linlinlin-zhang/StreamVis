from __future__ import annotations

import random
import uuid
from collections import deque
from typing import Any, Dict, List, Tuple

import networkx as nx


class IncrementalRenderer:
    def __init__(self, *, max_nodes: int = 60, max_edges: int = 120) -> None:
        self.graph = nx.Graph()
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Tuple[str, str]] = []
        self._node_order = deque()
        self._pos_norm: Dict[str, Tuple[float, float]] = {}
        self._width = 1000.0
        self._height = 700.0
        self._pad = 90.0
        self._scale = 0.38
        self._max_nodes = max(1, int(max_nodes))
        self._max_edges = max(0, int(max_edges))

    def clear(self) -> List[Dict[str, Any]]:
        self.nodes.clear()
        self.edges.clear()
        self.graph.clear()
        self._node_order.clear()
        self._pos_norm.clear()
        return [{"op": "clear"}]

    def generate_delta(self, intent: Dict[str, Any], context_vector: List[float]) -> List[Dict[str, Any]]:
        new_node_id = str(uuid.uuid4())[:8]
        label = f"Node {new_node_id}"
        value = float(random.randint(10, 100))

        self.nodes[new_node_id] = {"id": new_node_id, "label": label, "value": value}
        self.graph.add_node(new_node_id)
        self._node_order.append(new_node_id)

        ops: List[Dict[str, Any]] = [{"op": "add_node", "id": new_node_id, "label": label, "value": value}]

        if self.nodes and len(self.nodes) > 1:
            target_id = random.choice([k for k in self.nodes.keys() if k != new_node_id])
            self.edges.append((target_id, new_node_id))
            self.graph.add_edge(target_id, new_node_id)
            ops.append({"op": "add_edge", "source": target_id, "target": new_node_id})

        ops.extend(self._evict_over_budget())

        pos = self._update_layout()
        for nid, (x, y) in pos.items():
            ops.append({"op": "update_node", "id": nid, "x": x, "y": y})

        return ops

    def _evict_over_budget(self) -> List[Dict[str, Any]]:
        ops: List[Dict[str, Any]] = []

        while len(self.nodes) > self._max_nodes and self._node_order:
            victim = self._node_order.popleft()
            if victim not in self.nodes:
                continue
            removed_edges = [e for e in self.edges if victim in e]
            if removed_edges:
                self.edges = [e for e in self.edges if victim not in e]
                for a, b in removed_edges:
                    if self.graph.has_edge(a, b):
                        self.graph.remove_edge(a, b)
                    ops.append({"op": "remove_edge", "source": a, "target": b})
            if self.graph.has_node(victim):
                self.graph.remove_node(victim)
            self.nodes.pop(victim, None)
            self._pos_norm.pop(victim, None)
            ops.append({"op": "remove_node", "id": victim})

        if self._max_edges > 0:
            while len(self.edges) > self._max_edges:
                a, b = self.edges.pop(0)
                if self.graph.has_edge(a, b):
                    self.graph.remove_edge(a, b)
                ops.append({"op": "remove_edge", "source": a, "target": b})

        return ops

    def _update_layout(self) -> Dict[str, Tuple[float, float]]:
        if self.graph.number_of_nodes() == 0:
            return {}

        old_norm = dict(self._pos_norm)
        seed = 42
        raw = nx.spring_layout(
            self.graph,
            pos=old_norm if old_norm else None,
            seed=seed,
            iterations=40,
            scale=1.0,
            center=(0.0, 0.0),
        )

        lam = 0.86
        blended_norm: Dict[str, Tuple[float, float]] = {}
        for nid, p in raw.items():
            ox, oy = old_norm.get(nid, p)
            nxp = (1.0 - lam) * float(p[0]) + lam * float(ox)
            nyp = (1.0 - lam) * float(p[1]) + lam * float(oy)
            blended_norm[nid] = (nxp, nyp)

        self._pos_norm = blended_norm

        scaled: Dict[str, Tuple[float, float]] = {}
        cx = self._width / 2.0
        cy = self._height / 2.0
        rx = (self._width - 2 * self._pad) * self._scale
        ry = (self._height - 2 * self._pad) * self._scale
        for nid, (x, y) in blended_norm.items():
            sx = cx + x * rx
            sy = cy + y * ry
            sx = min(self._width - self._pad, max(self._pad, sx))
            sy = min(self._height - self._pad, max(self._pad, sy))
            scaled[nid] = (sx, sy)

        return scaled
