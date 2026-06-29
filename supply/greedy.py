"""The greedy baseline: a myopic dispatcher with no coordination.

The simplest thing a dispatcher can do: repeatedly take the cheapest lane still
available and ship as much as it can down it — limited by what the warehouse has
left and what the store still needs. Elastic demand is only served while it pays
(value at least covers the delivered cost).

It is fast and needs no solver, and on easy instances it even ties the optimum.
But it never looks ahead: committing a warehouse's scarce capacity to whichever
store happens to share its cheapest lane can strand a store that had no cheap
alternative, or burn supply on low-value demand. The gap between this and the
optimum is the cost of acting locally — the same lesson the DCOP demo tells with
conflicts, here measured in money.
"""
from __future__ import annotations

from .analysis import evaluate
from .model import Network


def solve_greedy(net: Network) -> dict:
    """Fill the cheapest available lane first; record one frame per shipment."""
    cap = {w.id: w.capacity for w in net.warehouses}
    dem = {s.id: s.demand for s in net.stores}
    # cheapest delivered cost first; ties broken by id for determinism
    lanes = sorted(net.lanes,
                   key=lambda l: (net.warehouse(l.src).cost + l.cost, l.src, l.dst))

    flow = {}
    frames = []
    for l in lanes:
        store = net.store(l.dst)
        delivered = net.warehouse(l.src).cost + l.cost
        if not store.mandatory and store.value < delivered:
            continue  # serving this unit would lose money
        qty = min(cap[l.src], dem[l.dst])
        if l.capacity is not None:
            qty = min(qty, l.capacity)
        if qty <= 0:
            continue
        flow[f"{l.src}->{l.dst}"] = flow.get(f"{l.src}->{l.dst}", 0.0) + qty
        cap[l.src] -= qty
        dem[l.dst] -= qty
        step = evaluate(net, flow)
        frames.append({
            "step": len(frames) + 1,
            "lane": f"{l.src}->{l.dst}",
            "qty": qty,
            "cost": step["cost"],
            "welfare": step.get("welfare"),
        })

    out = evaluate(net, flow)
    out["method"] = "greedy"
    out["flow"] = {k: round(v, 6) for k, v in flow.items()}
    out["frames"] = frames
    return out
