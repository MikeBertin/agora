"""Scoring a flow, and comparing the three solvers head to head.

``evaluate`` scores any flow — whoever produced it — on the one network, so the
central optimum, the market and the greedy baseline are judged on identical
terms. ``compare`` runs all three and reports the efficiency gap: how close a
decentralised market and a myopic baseline get to the planner's optimum.
"""
from __future__ import annotations

from typing import Dict

from .model import Network


def evaluate(net: Network, flow: Dict[str, float]) -> dict:
    """Score a flow: served/unserved, total cost, and welfare if any demand is elastic."""
    served = {s.id: 0.0 for s in net.stores}
    cost = 0.0
    for key, units in flow.items():
        wid, sid = key.split("->")
        served[sid] += units
        cost += (net.warehouse(wid).cost + net.lane(wid, sid).cost) * units
    served = {k: round(v, 6) for k, v in served.items()}
    unserved = {s.id: round(s.demand - served[s.id], 6) for s in net.stores}

    out = {
        "served": served,
        "unserved": unserved,
        "cost": round(cost, 6),
        "pctServed": round(100.0 * sum(served.values()) / net.total_demand(), 2),
    }
    elastic = [s for s in net.stores if not s.mandatory]
    if elastic:
        served_value = sum(net.store(s.id).value * served[s.id] for s in elastic)
        lost_value = sum(net.store(s.id).value * unserved[s.id] for s in elastic)
        out["servedValue"] = round(served_value, 6)
        out["lostValue"] = round(lost_value, 6)
        out["welfare"] = round(served_value - cost, 6)
    return out


def compare(net: Network) -> dict:
    """Run optimum, market and greedy; report each and the efficiency gap.

    Efficiency is a single [0, 1] score where 1 means optimal: a welfare ratio
    when demand is elastic, otherwise a cost ratio (optimum cost / method cost).
    A cost ratio only means anything when both methods serve the same demand, so
    a method that leaves mandatory demand unserved scores 0 (its row also gets
    ``feasible: False``). If the optimal welfare itself is not positive the
    ratio's direction inverts, so efficiency is then 1 for methods matching the
    optimum and None (undefined) otherwise.
    """
    # imported here to avoid a cycle: solvers import this module
    from .greedy import solve_greedy
    from .market import solve_market
    from .solve import solve_optimum

    elastic = not net.all_mandatory()
    opt = solve_optimum(net)
    if not opt.get("feasible", True):
        # mandatory demand can't be met — no optimum to compare against
        return {"network": net.to_dict(),
                "objective": "welfare" if elastic else "cost",
                "feasible": False, "methods": {"optimum": opt}}

    methods = {"optimum": opt, "market": solve_market(net), "greedy": solve_greedy(net)}

    rows = {}
    for name, r in methods.items():
        mand_ok = all(r["unserved"][s.id] <= 1e-6
                      for s in net.stores if s.mandatory)
        if not mand_ok:
            eff = 0.0  # served less than it had to; its cost/welfare is moot
        elif elastic:
            denom = opt["welfare"]
            if denom > 0:
                eff = min(1.0, r["welfare"] / denom)
            else:
                eff = 1.0 if abs(r["welfare"] - denom) <= 1e-6 else None
        else:
            eff = 1.0 if r["cost"] == 0 else min(1.0, opt["cost"] / r["cost"])
        rows[name] = {
            "cost": r["cost"],
            "welfare": r.get("welfare"),
            "pctServed": r.get("pctServed",
                               round(100.0 * sum(r["served"].values())
                                     / net.total_demand(), 2)),
            "feasible": mand_ok,
            "efficiency": None if eff is None else round(eff, 4),
        }

    return {
        "network": net.to_dict(),
        "objective": "welfare" if elastic else "cost",
        "methods": methods,
        "comparison": rows,
    }
