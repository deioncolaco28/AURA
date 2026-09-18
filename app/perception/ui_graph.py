"""
app/perception/ui_graph.py

Structured graph representation of visible UI elements and their relationships.

Supports:
- Hierarchical parent-child and ancestor relationships
- Sibling relationships within containers
- Semantic and functional grouping
- Spatial adjacency and neighbor queries
- Geometric containment inference from bounding boxes
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.perception.ui_element import UIElement


@dataclass
class UIElementNode:
    """A node in the UIElementGraph."""

    element: UIElement
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)
    group: str | None = None


class UIElementGraph:
    """
    Structured graph representing the visible user interface hierarchy and spatial topology.
    """

    def __init__(self):
        self._nodes: dict[str, UIElementNode] = {}
        self._root_ids: list[str] = []
        self._groups: dict[str, list[str]] = {}

    @property
    def element_count(self) -> int:
        return len(self._nodes)

    def add_element(
        self,
        element: UIElement,
        parent_id: str | None = None,
        group: str | None = None,
    ) -> None:
        """Add an element to the graph with optional parent relationship."""
        eid = element.element_id

        # Update element's internal parent_id if supplied
        if parent_id:
            element.parent_id = parent_id

        node = UIElementNode(
            element=element,
            parent_id=parent_id,
            children_ids=[],
            group=group or element.group,
        )

        self._nodes[eid] = node

        if parent_id and parent_id in self._nodes:
            if eid not in self._nodes[parent_id].children_ids:
                self._nodes[parent_id].children_ids.append(eid)
                self._nodes[parent_id].element.children_ids.append(eid)
        else:
            if eid not in self._root_ids:
                self._root_ids.append(eid)

        # Register group
        g = group or element.group
        if g:
            if g not in self._groups:
                self._groups[g] = []
            if eid not in self._groups[g]:
                self._groups[g].append(eid)

    def remove_element(self, element_id: str) -> None:
        """Remove an element and detach it from its parent and children."""
        if element_id not in self._nodes:
            return

        node = self._nodes[element_id]

        # Remove from parent's children
        if node.parent_id and node.parent_id in self._nodes:
            parent_node = self._nodes[node.parent_id]
            if element_id in parent_node.children_ids:
                parent_node.children_ids.remove(element_id)
            if element_id in parent_node.element.children_ids:
                parent_node.element.children_ids.remove(element_id)

        if element_id in self._root_ids:
            self._root_ids.remove(element_id)

        # Remove from groups
        for g_list in self._groups.values():
            if element_id in g_list:
                g_list.remove(element_id)

        del self._nodes[element_id]

    def get_element(self, element_id: str) -> UIElement | None:
        """Retrieve a UIElement by its ID."""
        node = self._nodes.get(element_id)
        return node.element if node else None

    def get_parent(self, element_id: str) -> UIElement | None:
        """Retrieve the parent UIElement."""
        node = self._nodes.get(element_id)
        if node and node.parent_id:
            return self.get_element(node.parent_id)
        return None

    def get_children(self, element_id: str) -> list[UIElement]:
        """Retrieve immediate child UIElements."""
        node = self._nodes.get(element_id)
        if not node:
            return []
        return [self._nodes[cid].element for cid in node.children_ids if cid in self._nodes]

    def get_siblings(self, element_id: str) -> list[UIElement]:
        """Retrieve sibling UIElements (sharing the same parent or root level)."""
        node = self._nodes.get(element_id)
        if not node:
            return []

        if node.parent_id:
            parent = self._nodes.get(node.parent_id)
            if parent:
                return [
                    self._nodes[cid].element
                    for cid in parent.children_ids
                    if cid != element_id and cid in self._nodes
                ]
            return []

        # Root level siblings
        return [
            self._nodes[rid].element
            for rid in self._root_ids
            if rid != element_id and rid in self._nodes
        ]

    def get_ancestors(self, element_id: str) -> list[UIElement]:
        """Retrieve list of ancestors from immediate parent up to root."""
        ancestors: list[UIElement] = []
        curr_id = element_id
        visited = set()

        while curr_id in self._nodes and curr_id not in visited:
            visited.add(curr_id)
            node = self._nodes[curr_id]
            if node.parent_id and node.parent_id in self._nodes:
                ancestors.append(self._nodes[node.parent_id].element)
                curr_id = node.parent_id
            else:
                break

        return ancestors

    def get_group(self, group_name: str) -> list[UIElement]:
        """Retrieve all UIElements belonging to a named group."""
        eids = self._groups.get(group_name, [])
        return [self._nodes[eid].element for eid in eids if eid in self._nodes]

    def find_by_text(self, text: str, exact: bool = False) -> list[UIElement]:
        """Find elements matching the given text label."""
        if not text:
            return []
        t_clean = text.strip().lower()
        matches: list[UIElement] = []

        for node in self._nodes.values():
            elem_text = (node.element.text or "").strip().lower()
            if exact and elem_text == t_clean:
                matches.append(node.element)
            elif not exact and t_clean in elem_text:
                matches.append(node.element)

        return matches

    def find_by_type(self, element_type: str) -> list[UIElement]:
        """Find elements matching the given element type."""
        t_clean = element_type.strip().lower()
        return [
            node.element
            for node in self._nodes.values()
            if node.element.element_type.lower() == t_clean
        ]

    def all_elements(self) -> list[UIElement]:
        """Return all UIElements in the graph."""
        return [node.element for node in self._nodes.values()]

    def get_spatial_neighbors(
        self,
        element_id: str,
        direction: str | None = None,
        radius: float | None = None,
        max_results: int = 5,
    ) -> list[UIElement]:
        """
        Find spatially adjacent neighbors of an element.

        direction: 'above', 'below', 'left', 'right', 'beside', or None (all directions).
        radius: maximum pixel distance (None for default 300px).
        """
        target = self.get_element(element_id)
        if not target:
            return []

        max_dist = radius or 300.0
        tx, ty = target.center
        candidates: list[tuple[float, UIElement]] = []

        for node in self._nodes.values():
            elem = node.element
            if elem.element_id == element_id:
                continue

            ex, ey = elem.center
            dx = ex - tx
            dy = ey - ty
            dist = math.hypot(dx, dy)

            if dist > max_dist:
                continue

            if direction == "above" and dy >= -10:
                continue
            if direction == "below" and dy <= 10:
                continue
            if direction == "left" and dx >= -10:
                continue
            if direction == "right" and dx <= 10:
                continue
            if direction == "beside" and abs(dy) > 40:
                continue

            candidates.append((dist, elem))

        candidates.sort(key=lambda item: item[0])
        return [elem for _, elem in candidates[:max_results]]

    @classmethod
    def build_from_elements(cls, elements: list[UIElement]) -> UIElementGraph:
        """
        Build a UIElementGraph from an unstructured list of UIElements.

        Infers hierarchical containment: larger bounding boxes containing smaller ones
        are established as parent containers.
        """
        graph = cls()
        if not elements:
            return graph

        # Sort elements by bounding box area descending (largest container first)
        sorted_elements = sorted(
            elements,
            key=lambda e: (e.area, -(e.x + e.y)),
            reverse=True,
        )

        for elem in sorted_elements:
            parent_id = None
            # If element already has explicit parent_id, use it
            if elem.parent_id and elem.parent_id in graph._nodes:
                parent_id = elem.parent_id
            else:
                # Find smallest existing node that fully contains this element
                smallest_container = None
                smallest_area = float("inf")

                for existing_id, existing_node in graph._nodes.items():
                    parent_candidate = existing_node.element
                    if cls._contains(parent_candidate, elem):
                        if parent_candidate.area < smallest_area:
                            smallest_area = parent_candidate.area
                            smallest_container = existing_id

                parent_id = smallest_container

            graph.add_element(elem, parent_id=parent_id)

        return graph

    @staticmethod
    def _contains(parent: UIElement, child: UIElement) -> bool:
        """Check if parent bounding box geometrically encloses child."""
        if parent.area <= child.area:
            return False

        # Allow slight boundary tolerance of 5px
        tol = 5
        return (
            parent.x - tol <= child.x
            and parent.y - tol <= child.y
            and parent.x + parent.width + tol >= child.x + child.width
            and parent.y + parent.height + tol >= child.y + child.height
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            "root_ids": list(self._root_ids),
            "groups": {k: list(v) for k, v in self._groups.items()},
            "nodes": {
                eid: {
                    "parent_id": node.parent_id,
                    "children_ids": list(node.children_ids),
                    "group": node.group,
                    "element": {
                        "element_id": node.element.element_id,
                        "element_type": node.element.element_type,
                        "text": node.element.text,
                        "x": node.element.x,
                        "y": node.element.y,
                        "width": node.element.width,
                        "height": node.element.height,
                        "confidence": node.element.confidence,
                        "source": node.element.source,
                        "stable_id": node.element.stable_id,
                    },
                }
                for eid, node in self._nodes.items()
            },
        }
