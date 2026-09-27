"""Curated logistics scenarios, each illustrating one lesson in supply allocation.

Costs and capacities are small round numbers so every optimum can be checked by
hand (see tests). Positions are on the unit square for the map view; lane costs
are given explicitly rather than derived from distance, the way real freight
rates rarely match the crow-flies distance.
"""
from __future__ import annotations

import random
from typing import Dict, List, Tuple

from .model import Lane, Network, Store, Warehouse


def _lanes(costs: Dict[Tuple[str, str], float]) -> List[Lane]:
    """Build an uncapacitated lane for every (warehouse, store) cost entry."""
    return [Lane(src, dst, cost) for (src, dst), cost in costs.items()]


def regions() -> Network:
    """Balanced regions: who serves the swing store decides the bill."""
    warehouses = [
        Warehouse("W1", "West DC", 30, 0.15, 0.50),
        Warehouse("W2", "East DC", 30, 0.85, 0.50),
    ]
    stores = [
        Store("S1", "Westgate", 20, 0.20, 0.18),
        Store("S2", "Eastgate", 20, 0.80, 0.18),
        Store("S3", "Midtown", 20, 0.50, 0.85),
    ]
    costs = {
        ("W1", "S1"): 2, ("W1", "S2"): 8, ("W1", "S3"): 5,
        ("W2", "S1"): 8, ("W2", "S2"): 2, ("W2", "S3"): 5,
    }
    return Network("Regional balance", warehouses, stores, _lanes(costs))


def bottleneck() -> Network:
    """Scarce cheap capacity: the marginal (expensive) unit sets the price."""
    warehouses = [
        Warehouse("W1", "Cheap DC", 20, 0.20, 0.30),
        Warehouse("W2", "Pricey DC", 60, 0.80, 0.30),
    ]
    stores = [
        Store("S1", "North store", 25, 0.35, 0.75),
        Store("S2", "South store", 25, 0.65, 0.75),
    ]
    costs = {
        ("W1", "S1"): 1, ("W1", "S2"): 1,
        ("W2", "S1"): 6, ("W2", "S2"): 6,
    }
    return Network("Capacity bottleneck", warehouses, stores, _lanes(costs))


def shortage() -> Network:
    """Not enough to go round: with elastic demand, *what* you serve matters.

    Supply (30) is short of demand (40), and demand is elastic: each store has
    a per-unit value. The cheapest lane reaches the low-value store, so a
    cost-myopic plan fills it first and wastes scarce supply; the welfare
    optimum serves the high-value store first instead.
    """
    warehouses = [
        Warehouse("W1", "Central DC", 30, 0.50, 0.20),
    ]
    stores = [
        Store("S1", "Flagship", 20, 0.25, 0.78, value=10),
        Store("S2", "Outlet", 20, 0.75, 0.78, value=3),
    ]
    costs = {
        ("W1", "S1"): 4,
        ("W1", "S2"): 1,
    }
    return Network("Shortage & elastic demand", warehouses, stores, _lanes(costs))


def myopia() -> Network:
    """Greedy's blind spot: the single cheapest lane steals needed capacity.

    The Hub is the only cheap way to reach the Remote store, but it is *also*
    the single cheapest lane to the Easy store, which has a fine backup in the
    Depot. A myopic dispatcher grabs that cheapest lane first, exhausts the Hub
    on the Easy store, and is left shipping to the Remote store at 9×. Planning
    ahead sends the Hub to the Remote store instead and halves the bill.
    """
    warehouses = [
        Warehouse("W1", "Hub", 10, 0.25, 0.55),
        Warehouse("W2", "Depot", 10, 0.80, 0.50),
    ]
    stores = [
        Store("S1", "Easy store", 10, 0.50, 0.20),
        Store("S2", "Remote store", 10, 0.18, 0.85),
    ]
    costs = {
        ("W1", "S1"): 1, ("W1", "S2"): 2,
        ("W2", "S1"): 3, ("W2", "S2"): 9,
    }
    return Network("Greedy's blind spot", warehouses, stores, _lanes(costs))


def stranded() -> Network:
    """No backup route: greedy leaves a whole store with nothing.

    The Coastal DC has no lane to the Valley store; only the Junction reaches
    it. But the Junction's cheapest lane is to the City store (which the Coastal
    DC could have covered). Greedy spends the Junction's stock on the City lane
    and the Valley gets zero: the plan is cheap per unit shipped but fails half
    the network. Its efficiency is 0, since cost comparisons mean nothing when you
    don't serve the same demand.
    """
    warehouses = [
        Warehouse("W1", "Junction DC", 10, 0.45, 0.40),
        Warehouse("W2", "Coastal DC", 10, 0.90, 0.60),
    ]
    stores = [
        Store("S1", "City store", 10, 0.65, 0.75),
        Store("S2", "Valley store", 10, 0.12, 0.65),
    ]
    costs = {
        ("W1", "S1"): 1, ("W1", "S2"): 2,
        ("W2", "S1"): 3,               # the Coastal DC cannot reach the Valley
    }
    return Network("Stranded store", warehouses, stores, _lanes(costs))


def random_network(m: int, n: int, seed: int,
                   demand: Tuple[int, int] = (10, 30),
                   elastic_share: float = 0.25,
                   headroom: float = 1.25,
                   density: float = 0.7,
                   cost: Tuple[int, int] = (1, 20)) -> Network:
    """A random instance for benchmarks and stress tests, deterministic per seed.

    Integer costs and units throughout (the auction's ε-optimality guarantee
    needs integers). Total capacity is ``headroom`` × total demand, spread
    unevenly over ``m`` warehouses; each of the ``n`` stores is elastic with
    probability ``elastic_share``; lanes exist with probability ``density``,
    topped up so every mandatory store can reach enough capacity. Deeper
    (Hall-type) infeasibility is still possible but rare, so check the LP's
    ``feasible`` flag if it matters.
    """
    rng = random.Random(seed)
    stores = []
    for j in range(n):
        val = rng.randint(5, 30) if rng.random() < elastic_share else None
        stores.append(Store(f"S{j+1}", f"Store {j+1}", rng.randint(*demand),
                            round(rng.random(), 3), round(rng.random(), 3),
                            value=val))
    total = sum(int(s.demand) for s in stores)
    base = max(1, int(headroom * total / m))
    caps = [rng.randint(max(1, int(0.7 * base)), int(1.3 * base) + 1)
            for _ in range(m)]
    caps[0] += max(0, total - sum(caps))  # never less capacity than demand
    warehouses = [Warehouse(f"W{i+1}", f"DC {i+1}", caps[i],
                            round(rng.random(), 3), round(rng.random(), 3),
                            cost=rng.randint(0, 3))
                  for i in range(m)]
    lanes = {}
    for w in warehouses:
        for s in stores:
            if rng.random() < density:
                lanes[(w.id, s.id)] = Lane(w.id, s.id, rng.randint(*cost))
    for s in stores:  # top up reachability for mandatory demand
        if not s.mandatory:
            continue
        reach = lambda: sum(w.capacity for w in warehouses
                            if (w.id, s.id) in lanes)
        pool = [w for w in warehouses if (w.id, s.id) not in lanes]
        rng.shuffle(pool)
        while reach() < s.demand and pool:
            w = pool.pop()
            lanes[(w.id, s.id)] = Lane(w.id, s.id, rng.randint(*cost))
    return Network(f"random {m}x{n} #{seed}", warehouses, stores,
                   list(lanes.values()))


SCENARIOS = [
    {
        "id": "regions",
        "label": "Regional balance",
        "blurb": "Two regional DCs, three stores. Each DC cheaply serves its own "
                 "side; the Midtown store sits between them and is the swing: how "
                 "its 20 units split is what the optimiser actually decides.",
        "network": regions(),
    },
    {
        "id": "bottleneck",
        "label": "Capacity bottleneck",
        "blurb": "The cheap DC can only cover 20 of the 50 units demanded, so the "
                 "rest must ship from the pricey DC at 6×. The last unit served "
                 "costs 6, and that marginal cost becomes the market price "
                 "everywhere, handing the cheap DC's scarce capacity a premium.",
        "network": bottleneck(),
    },
    {
        "id": "shortage",
        "label": "Shortage & elastic demand",
        "blurb": "Only 30 units for 40 of demand. The Outlet is cheapest to reach "
                 "but its goods are worth little; the Flagship is dearer to serve "
                 "but far more valuable. Serve the right one and welfare is high; "
                 "grab the nearest and you leave money on the table.",
        "network": shortage(),
    },
    {
        "id": "myopia",
        "label": "Greedy's blind spot",
        "blurb": "Both stores must be served. The Hub is cheapest of all to the "
                 "Easy store, but the Easy store has a backup and the Remote one "
                 "doesn't. Grab the cheapest lane and you pay 9× to reach the "
                 "Remote store; plan ahead and the bill halves, 100 down to 50.",
        "network": myopia(),
    },
    {
        "id": "stranded",
        "label": "Stranded store",
        "blurb": "Only the Junction DC can reach the Valley store, but its "
                 "cheapest lane goes to the City, which the Coastal DC could have "
                 "covered. Greedy burns the Junction's stock on that cheap lane "
                 "and the Valley gets nothing: half the demand unserved, "
                 "efficiency zero. The market and the optimum plan backwards "
                 "from the constraint.",
        "network": stranded(),
    },
]

BY_ID = {s["id"]: s for s in SCENARIOS}
