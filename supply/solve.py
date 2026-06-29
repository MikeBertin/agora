"""Central optimum: the transportation problem as a linear program.

We choose how many units flow on each lane to **minimise total cost** — handling
plus shipping on every served unit, plus the *lost value* of any demand left
unserved. Pricing unserved elastic demand at its own value is the trick that
folds two problems into one LP:

  * mandatory demand (``value is None``) has no unserved variable, so it must be
    met in full — the pure min-cost transportation problem; and
  * elastic demand can go unserved at the cost of its value, so minimising total
    cost is exactly **maximising welfare** (served value minus cost).

This is solved exactly by HiGHS via scipy's ``linprog``. The real prize is the
**dual**:

  * the multiplier on each store's demand constraint is the market-clearing
    **price** there — the marginal cost of serving one more unit; and
  * the multiplier on each warehouse's capacity constraint is its **rent** — how
    much total cost would fall given one more unit of that scarce capacity.

By LP duality the optimum satisfies  cost = Σ price·demand − Σ rent·capacity.
"""
from __future__ import annotations

from typing import Dict

from scipy.optimize import linprog

from .model import Network

_EPS = 1e-7


def solve_optimum(net: Network) -> dict:
    """Solve a Network to optimality and return flow, cost/welfare and duals."""
    lanes = net.lanes
    stores = net.stores
    elastic = [s for s in stores if not s.mandatory]

    # --- variables: one per lane, plus one "unserved" slack per elastic store
    c: list = []
    bounds: list = []
    lane_col: Dict[int, int] = {}
    for li, l in enumerate(lanes):
        lane_col[li] = len(c)
        c.append(net.warehouse(l.src).cost + l.cost)
        bounds.append((0, l.capacity))
    uns_col: Dict[str, int] = {}
    for s in elastic:
        uns_col[s.id] = len(c)
        c.append(s.value)
        bounds.append((0, None))
    nvar = len(c)

    # --- demand: every store's demand is met by inflow (+ unserved if elastic)
    A_eq, b_eq, store_row = [], [], {}
    for s in stores:
        row = [0.0] * nvar
        for li, l in enumerate(lanes):
            if l.dst == s.id:
                row[lane_col[li]] = 1.0
        if not s.mandatory:
            row[uns_col[s.id]] = 1.0
        store_row[s.id] = len(A_eq)
        A_eq.append(row)
        b_eq.append(s.demand)

    # --- supply: each warehouse ships at most its capacity
    A_ub, b_ub, wh_row = [], [], {}
    for w in net.warehouses:
        row = [0.0] * nvar
        for li, l in enumerate(lanes):
            if l.src == w.id:
                row[lane_col[li]] = 1.0
        wh_row[w.id] = len(A_ub)
        A_ub.append(row)
        b_ub.append(w.capacity)

    res = linprog(c, A_ub=A_ub or None, b_ub=b_ub or None,
                  A_eq=A_eq or None, b_eq=b_eq or None,
                  bounds=bounds, method="highs")
    if not res.success:
        return {"method": "optimum", "feasible": False, "message": res.message}

    x = res.x
    flow = {}
    served = {s.id: 0.0 for s in stores}
    cost = 0.0
    for li, l in enumerate(lanes):
        units = float(x[lane_col[li]])
        if units > _EPS:
            flow[f"{l.src}->{l.dst}"] = round(units, 6)
            served[l.dst] += units
            cost += (net.warehouse(l.src).cost + l.cost) * units
    served = {k: round(v, 6) for k, v in served.items()}
    unserved = {s.id: round(s.demand - served[s.id], 6) for s in stores}

    # Duals. linprog (HiGHS) reports marginals as d(objective)/d(bound):
    #   demand eq -> +marginal is the marginal cost of one more unit = price
    #   supply <= -> -marginal is the saving from one more unit = capacity rent
    prices = {sid: round(float(res.eqlin.marginals[r]), 6)
              for sid, r in store_row.items()}
    rents = {wid: round(float(-res.ineqlin.marginals[r]), 6)
             for wid, r in wh_row.items()}

    out = {
        "method": "optimum",
        "feasible": True,
        "flow": flow,
        "served": served,
        "unserved": unserved,
        "cost": round(cost, 6),
        "prices": prices,
        "rents": rents,
    }
    if elastic:
        served_value = sum(net.store(s.id).value * served[s.id] for s in elastic)
        lost_value = sum(net.store(s.id).value * unserved[s.id] for s in elastic)
        out["servedValue"] = round(served_value, 6)
        out["lostValue"] = round(lost_value, 6)
        out["welfare"] = round(served_value - cost, 6)
    return out
