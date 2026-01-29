from __future__ import annotations

import random
import uuid
from typing import Any, Dict, List


class IncrementalRenderer:
    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []

    def clear(self) -> List[Dict[str, Any]]:
        self.nodes.clear()
        self.edges.clear()
        return [{"op": "clear"}]

    def generate_delta(self, intent: Dict[str, Any], context_vector: List[float]) -> List[Dict[str, Any]]:
        new_node_id = str(uuid.uuid4())[:8]
        label = f"Node {new_node_id}"
        value = float(random.randint(10, 100))

        ops: List[Dict[str, Any]] = [{"op": "add_node", "id": new_node_id, "label": label, "value": value}]

        if self.nodes:
            target_id = random.choice(list(self.nodes.keys()))
            ops.append({"op": "add_edge", "source": target_id, "target": new_node_id})

        self.nodes[new_node_id] = {"id": new_node_id, "label": label, "value": value}
        return ops
