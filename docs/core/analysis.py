"""Exact outcome-space analysis (the domain is small enough to enumerate).

Computes, over every possible bid, the Pareto frontier and the Nash bargaining
point so the bid-dance panel can show how close a negotiated deal landed to the
optimal trade-offs.
"""
from __future__ import annotations

from typing import Dict, List

from .domain import Domain
from .domain import UtilitySpace


def outcome_space(domain: Domain, ua: UtilitySpace, ub: UtilitySpace) -> List[dict]:
    pts = []
    for bid in domain.all_bids():
        pts.append({"bid": bid, "utilA": ua.utility(bid), "utilB": ub.utility(bid)})
    return pts


def pareto_frontier(points: List[dict]) -> List[dict]:
    """Points not dominated by any other (both utilities <=, one strictly <)."""
    frontier = []
    for p in points:
        dominated = False
        for q in points:
            if q is p:
                continue
            if (q["utilA"] >= p["utilA"] and q["utilB"] >= p["utilB"] and
                    (q["utilA"] > p["utilA"] or q["utilB"] > p["utilB"])):
                dominated = True
                break
        if not dominated:
            frontier.append(p)
    frontier.sort(key=lambda p: p["utilA"])
    return frontier


def nash_point(points: List[dict], res_a: float, res_b: float) -> dict:
    """Bid maximising the product of surpluses over the reservation values."""
    best, best_prod = None, -1.0
    for p in points:
        prod = max(0.0, p["utilA"] - res_a) * max(0.0, p["utilB"] - res_b)
        if prod > best_prod:
            best_prod, best = prod, p
    return best


def analyse(domain: Domain, ua: UtilitySpace, ub: UtilitySpace) -> dict:
    pts = outcome_space(domain, ua, ub)
    frontier = pareto_frontier(pts)
    return {
        "outcomes": [{"utilA": round(p["utilA"], 4), "utilB": round(p["utilB"], 4)}
                     for p in pts],
        "paretoFrontier": [{"utilA": round(p["utilA"], 4), "utilB": round(p["utilB"], 4)}
                           for p in frontier],
        "nash": _round_pt(nash_point(pts, ua.reservation, ub.reservation)),
    }


def _round_pt(p: dict) -> dict:
    return {"utilA": round(p["utilA"], 4), "utilB": round(p["utilB"], 4), "bid": p["bid"]}
