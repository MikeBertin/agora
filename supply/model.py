"""Transportation networks for logistics supply allocation.

A Network is a bipartite shipping problem: warehouses hold a limited supply of
a single homogeneous good and ship it down lanes to stores that demand it.
Every lane has a per-unit shipping cost; serving a unit of a store's demand is
worth its per-unit value. A solver's job is to choose how many units flow on
each lane — a Flow.

The model is deliberately plain data. Every solver — the central LP optimum,
the auction-algorithm market, and the greedy baseline — reads the same Network
and returns a Flow, so they can be compared on equal footing.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# A Flow assigns a number of units to each lane, keyed by (warehouse, store).
Flow = Dict[Tuple[str, str], float]


class Warehouse:
    """A supply node: up to ``capacity`` units, at ``cost`` each to handle."""

    def __init__(self, id: str, name: str, capacity: float,
                 x: float, y: float, cost: float = 0.0):
        self.id = id
        self.name = name
        self.capacity = capacity
        self.x = x
        self.y = y
        self.cost = cost  # per-unit handling/production cost


class Store:
    """A demand node wanting ``demand`` units, each worth ``value`` if served.

    ``value=None`` marks the demand as *mandatory*: it must be served in full
    (the pure min-cost transportation problem). A finite value makes demand
    *elastic* — a unit is only worth serving when its value exceeds the
    delivered cost, so the welfare-maximising solution may leave low-value
    demand unmet.
    """

    def __init__(self, id: str, name: str, demand: float,
                 x: float, y: float, value: Optional[float] = None):
        self.id = id
        self.name = name
        self.demand = demand
        self.x = x
        self.y = y
        self.value = value

    @property
    def mandatory(self) -> bool:
        return self.value is None


class Lane:
    """A directed shipping arc warehouse->store at ``cost`` per unit.

    ``capacity=None`` means the lane is uncapacitated (the only ceiling is the
    warehouse's supply and the store's demand).
    """

    def __init__(self, src: str, dst: str, cost: float,
                 capacity: Optional[float] = None):
        self.src = src
        self.dst = dst
        self.cost = cost
        self.capacity = capacity


class Network:
    """A bipartite transportation instance: warehouses, stores and lanes."""

    def __init__(self, name: str, warehouses: List[Warehouse],
                 stores: List[Store], lanes: List[Lane]):
        self.name = name
        self.warehouses = warehouses
        self.stores = stores
        self.lanes = lanes
        self._wh = {w.id: w for w in warehouses}
        self._st = {s.id: s for s in stores}
        self._lane = {(l.src, l.dst): l for l in lanes}
        self._validate()

    def _validate(self) -> None:
        assert len(self._wh) == len(self.warehouses), "duplicate warehouse id"
        assert len(self._st) == len(self.stores), "duplicate store id"
        for l in self.lanes:
            assert l.src in self._wh, f"lane from unknown warehouse {l.src!r}"
            assert l.dst in self._st, f"lane to unknown store {l.dst!r}"

    # --- lookups -----------------------------------------------------------
    def warehouse(self, wid: str) -> Warehouse:
        return self._wh[wid]

    def store(self, sid: str) -> Store:
        return self._st[sid]

    def lane(self, src: str, dst: str) -> Optional[Lane]:
        return self._lane.get((src, dst))

    def lanes_from(self, src: str) -> List[Lane]:
        return [l for l in self.lanes if l.src == src]

    def lanes_to(self, dst: str) -> List[Lane]:
        return [l for l in self.lanes if l.dst == dst]

    # --- totals ------------------------------------------------------------
    def total_supply(self) -> float:
        return sum(w.capacity for w in self.warehouses)

    def total_demand(self) -> float:
        return sum(s.demand for s in self.stores)

    def is_balanced(self) -> bool:
        return self.total_supply() == self.total_demand()

    def all_mandatory(self) -> bool:
        """True when every store's demand must be served in full."""
        return all(s.mandatory for s in self.stores)

    # --- serialisation -----------------------------------------------------
    def to_dict(self) -> dict:
        """JSON-serialisable form, consumed by the web demo."""
        return {
            "name": self.name,
            "warehouses": [
                {"id": w.id, "name": w.name, "capacity": w.capacity,
                 "x": w.x, "y": w.y, "cost": w.cost}
                for w in self.warehouses
            ],
            "stores": [
                {"id": s.id, "name": s.name, "demand": s.demand,
                 "x": s.x, "y": s.y, "value": s.value}
                for s in self.stores
            ],
            "lanes": [
                {"src": l.src, "dst": l.dst, "cost": l.cost,
                 "capacity": l.capacity}
                for l in self.lanes
            ],
        }
