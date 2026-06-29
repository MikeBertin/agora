"""The market: Bertsekas' auction algorithm as a decentralised mechanism.

Where ``solve.py`` hands the whole instance to a central LP, here the allocation
*emerges* from self-interested bidding — the same idea as the single-item
auctions demo, scaled up to many units of supply and demand.

We disaggregate the transportation problem into an **assignment** problem: each
unit of a store's demand is a *buyer*, each unit of a warehouse's capacity is an
*object*. The benefit of matching a buyer (store s) to an object (warehouse w) is
the surplus it creates,

    a = value(s) - handling(w) - shipping(w, s),

so the maximum-surplus assignment is exactly the welfare optimum. Elastic demand
also has an *outside option* worth 0 (stay unserved); mandatory demand does not,
so it is always assigned (its value is treated as effectively unbounded).

The auction itself: every unassigned buyer simultaneously bids for the object
giving it the most surplus net of price, raising that object's price by its
advantage over its second-best plus a small ``eps``. Objects go to their highest
bidder; the dispossessed rebid next round. Prices only ever rise, so it
terminates, and for ``eps < 1/n`` (integer benefits) the assignment is optimal —
and the converged object prices are exactly the warehouses' capacity rents.

Bidding happens in synchronous rounds (every agent at once), which is both the
decentralised story and the source of the playback frames. The price war can run
to thousands of tiny steps, so the returned frames are downsampled for the demo;
the underlying round count is reported in full.
"""
from __future__ import annotations

from typing import List, Optional

from .model import Network

_NEG = float("-inf")
_DUMMY = -1  # the "stay unserved" outside option (elastic buyers only)


def solve_market(net: Network, eps: Optional[float] = None,
                 max_frames: int = 120, max_rounds: int = 200000) -> dict:
    """Run the auction to a clearing allocation; return it with playback frames."""
    # --- disaggregate into unit buyers (demand) and unit objects (capacity)
    buyers = []   # each: (store_id, value_or_None, mandatory)
    for s in net.stores:
        buyers += [(s.id, s.value, s.mandatory)] * int(s.demand)
    obj_wh = []   # warehouse id behind each object (one per capacity unit)
    for w in net.warehouses:
        obj_wh += [w.id] * int(w.capacity)
    nB, nK = len(buyers), len(obj_wh)

    # Big value so mandatory demand always prefers being served to anything.
    big = 1.0 + max((s.value or 0) for s in net.stores) \
        + max(w.cost for w in net.warehouses) \
        + max(l.cost for l in net.lanes)

    def benefit(b: int, k: int) -> float:
        sid, val, mand = buyers[b]
        lane = net.lane(obj_wh[k], sid)
        if lane is None:
            return _NEG  # no route from this warehouse to this store
        v = big if mand else val
        return v - net.warehouse(obj_wh[k]).cost - lane.cost

    if eps is None:
        eps = 1.0 / (nB + 1)  # < 1/n => optimal for integer benefits

    price = [0.0] * nK
    owner: List[Optional[int]] = [None] * nK   # object -> buyer
    held: List[Optional[int]] = [None] * nB    # buyer -> object (or _DUMMY)
    raw: list = []
    rounds = 0

    while True:
        free = [b for b in range(nB) if held[b] is None]
        if not free or rounds >= max_rounds:
            break
        rounds += 1
        bids = {}  # object -> (amount, buyer)
        for b in free:
            mand = buyers[b][2]
            best_k, best_v, second_v = _DUMMY, (_NEG if mand else 0.0), _NEG
            for k in range(nK):
                a = benefit(b, k)
                if a == _NEG:
                    continue
                net_v = a - price[k]
                if net_v > best_v:
                    second_v, best_v, best_k = best_v, net_v, k
                elif net_v > second_v:
                    second_v = net_v
            if best_k == _DUMMY:
                held[b] = _DUMMY  # not worth serving — leaves the market
                continue
            if second_v == _NEG:
                second_v = best_v  # sole option: minimal raise
            bid = benefit(b, best_k) - second_v + eps
            cur, who = bids.get(best_k, (_NEG, -1))
            if bid > cur or (bid == cur and b < who):
                bids[best_k] = (bid, b)
        for k, (amount, b) in bids.items():
            if owner[k] is not None:
                held[owner[k]] = None
            owner[k] = b
            held[b] = k
            price[k] = amount
        raw.append(_frame(net, buyers, obj_wh, held, price, rounds))

    frames = _downsample(raw, max_frames)
    return _result(net, buyers, obj_wh, held, price, frames, rounds, eps)


def _downsample(frames: list, k: int) -> list:
    """Keep at most k frames, evenly spaced, always including the last."""
    n = len(frames)
    if n <= k:
        return frames
    idx = sorted({round(i * (n - 1) / (k - 1)) for i in range(k)} | {n - 1})
    return [frames[i] for i in idx]


# --- aggregation / reporting ----------------------------------------------

def _aggregate_flow(net, buyers, obj_wh, held):
    """Collapse the unit assignment back to per-lane flow and per-store served."""
    flow = {}
    served = {s.id: 0.0 for s in net.stores}
    for b, k in enumerate(held):
        if k is None or k == _DUMMY:
            continue
        key = f"{obj_wh[k]}->{buyers[b][0]}"
        flow[key] = flow.get(key, 0.0) + 1.0
        served[buyers[b][0]] += 1.0
    return flow, served


def _cost_welfare(net, flow, served):
    cost = 0.0
    for key, units in flow.items():
        wid, sid = key.split("->")
        cost += (net.warehouse(wid).cost + net.lane(wid, sid).cost) * units
    elastic = [s for s in net.stores if not s.mandatory]
    served_value = sum(s.value * served[s.id] for s in elastic)
    return cost, served_value, elastic


def _warehouse_prices(net, obj_wh, held, price):
    """Clearing price behind each warehouse: the dearest of its sold units."""
    wp = {w.id: 0.0 for w in net.warehouses}
    for b, k in enumerate(held):
        if k is not None and k != _DUMMY:
            wp[obj_wh[k]] = max(wp[obj_wh[k]], price[k])
    return {w: round(v, 6) for w, v in wp.items()}


def _frame(net, buyers, obj_wh, held, price, rnd):
    flow, served = _aggregate_flow(net, buyers, obj_wh, held)
    cost, served_value, elastic = _cost_welfare(net, flow, served)
    return {
        "round": rnd,
        "assigned": sum(1 for k in held if k is not None and k != _DUMMY),
        "unserved": sum(1 for k in held if k == _DUMMY),
        "bidding": sum(1 for k in held if k is None),
        "cost": round(cost, 4),
        "welfare": round(served_value - cost, 4) if elastic else None,
        "warehousePrice": _warehouse_prices(net, obj_wh, held, price),
    }


def _result(net, buyers, obj_wh, held, price, frames, rounds, eps):
    flow, served = _aggregate_flow(net, buyers, obj_wh, held)
    served = {k: round(v, 6) for k, v in served.items()}
    unserved = {s.id: round(s.demand - served[s.id], 6) for s in net.stores}
    cost, served_value, elastic = _cost_welfare(net, flow, served)
    out = {
        "method": "market",
        "feasible": all(v <= 1e-6 for s, v in unserved.items()
                        if net.store(s).mandatory),
        "rounds": rounds,
        "eps": round(eps, 8),
        "flow": {k: round(v, 6) for k, v in flow.items()},
        "served": served,
        "unserved": unserved,
        "cost": round(cost, 6),
        "warehousePrice": _warehouse_prices(net, obj_wh, held, price),
        "frames": frames,
    }
    if elastic:
        out["servedValue"] = round(served_value, 6)
        out["lostValue"] = round(sum(s.value * unserved[s.id] for s in elastic), 6)
        out["welfare"] = round(served_value - cost, 6)
    return out
