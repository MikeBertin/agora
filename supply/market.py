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

Lane capacities need one more idea. A capped lane (w, s) limits how many of w's
units may travel to s specifically, so when any lane is capped the objects
become **lane slots**: lane (w, s) offers min(lane cap, capacity, demand) slots
that only s's buyers may bid on. A warehouse's slots can then add up to more
than its capacity, so the excess is retired by **phantom buyers** — one per
surplus slot, mandatory, indifferent between the warehouse's slots (benefit 0).
Every phantom must end up holding a slot, which is exactly the capacity
constraint; being indifferent, they settle on the slots real demand values
least, and their arbitrage across a warehouse's pools is what keeps its slot
prices coherent. Uncapacitated networks skip all this and use the plain
warehouse-unit disaggregation.

The auction itself: every unassigned buyer simultaneously bids for the object
giving it the most surplus net of price, raising that object's price by its
advantage over its second-best plus a small ``eps``. Objects go to their highest
bidder; the dispossessed rebid next round. Prices only ever rise, so it
terminates, and for ``eps < 1/n`` (integer benefits) the assignment is optimal —
and the converged object prices are exactly the warehouses' capacity rents
(plus the lane's own rent, on a binding capped lane).

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
    """Run the auction to a clearing allocation; return it with playback frames.

    The unit disaggregation needs whole units: every demand, capacity and finite
    lane capacity must be an integer (the LP and greedy handle fractional
    amounts; the auction cannot, and truncating would silently solve a
    different instance).
    """
    for s in net.stores:
        if s.demand != int(s.demand):
            raise ValueError(f"market needs integer demand; {s.id} has {s.demand}")
    for w in net.warehouses:
        if w.capacity != int(w.capacity):
            raise ValueError(f"market needs integer capacity; {w.id} has {w.capacity}")
    for l in net.lanes:
        if l.capacity is not None and l.capacity != int(l.capacity):
            raise ValueError(f"market needs integer lane capacity; "
                             f"{l.src}->{l.dst} has {l.capacity}")

    capped = any(l.capacity is not None for l in net.lanes)

    # --- disaggregate into unit buyers (demand) and unit objects (capacity)
    buyers = []   # each: (store_id, value_or_None, mandatory, phantom_warehouse)
    for s in net.stores:
        buyers += [(s.id, s.value, s.mandatory, None)] * int(s.demand)

    obj_wh = []   # warehouse behind each object
    obj_st = []   # store the object may serve (None: any the lanes allow)
    slots_to = {s.id: 0 for s in net.stores}  # reachable capacity per store
    if capped:
        for w in net.warehouses:
            t = 0
            for l in net.lanes_from(w.id):
                n = int(min(l.capacity if l.capacity is not None else w.capacity,
                            w.capacity, net.store(l.dst).demand))
                obj_wh += [w.id] * n
                obj_st += [l.dst] * n
                slots_to[l.dst] += n
                t += n
            # phantom buyers retire the slots beyond the warehouse's capacity
            buyers += [(None, None, True, w.id)] * max(0, t - int(w.capacity))
    else:
        for w in net.warehouses:
            obj_wh += [w.id] * int(w.capacity)
            for l in net.lanes_from(w.id):
                slots_to[l.dst] += int(min(w.capacity, net.store(l.dst).demand))
        obj_st = [None] * len(obj_wh)
    nB, nK = len(buyers), len(obj_wh)

    # Big value so mandatory demand always prefers being served to anything.
    big = 1.0 + max(((s.value or 0) for s in net.stores), default=0) \
        + max((w.cost for w in net.warehouses), default=0) \
        + max((l.cost for l in net.lanes), default=0)

    def benefit(b: int, k: int) -> float:
        sid, val, mand, ph = buyers[b]
        if ph is not None:
            # phantoms retire any slot of their own warehouse, worth nothing
            return 0.0 if obj_wh[k] == ph else _NEG
        if obj_st[k] is not None and obj_st[k] != sid:
            return _NEG  # a lane slot only serves its own store
        lane = net.lane(obj_wh[k], sid)
        if lane is None:
            return _NEG  # no route from this warehouse to this store
        v = big if mand else val
        return v - net.warehouse(obj_wh[k]).cost - lane.cost

    if eps is None:
        eps = 1.0 / (nB + 1)  # < 1/n => optimal for integer benefits

    # Mandatory demand that can never be served — capacity short overall, or
    # too little reachable via a store's lanes — would bid up to max_rounds;
    # bail out instead of letting the never-placeable buyers spin.
    mand_units = sum(int(s.demand) for s in net.stores if s.mandatory)
    total_cap = sum(int(w.capacity) for w in net.warehouses)
    if mand_units > total_cap or any(
            s.mandatory and int(s.demand) > slots_to[s.id] for s in net.stores):
        return _result(net, buyers, obj_wh, obj_st,
                       [None] * nB, [0.0] * nK, [], 0, eps, capped)

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
    return _result(net, buyers, obj_wh, obj_st, held, price,
                   frames, rounds, eps, capped)


def _downsample(frames: list, k: int) -> list:
    """Keep at most k frames, evenly spaced, always including the last."""
    n = len(frames)
    if n <= k:
        return frames
    if k < 2:
        return frames[-1:]
    idx = sorted({round(i * (n - 1) / (k - 1)) for i in range(k)} | {n - 1})
    return [frames[i] for i in idx]


# --- aggregation / reporting ----------------------------------------------

def _aggregate_flow(net, buyers, obj_wh, held):
    """Collapse the unit assignment back to per-lane flow and per-store served."""
    flow = {}
    served = {s.id: 0.0 for s in net.stores}
    for b, k in enumerate(held):
        if k is None or k == _DUMMY or buyers[b][3] is not None:
            continue  # unplaced, unserved, or a phantom retiring capacity
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


def _warehouse_prices(net, buyers, obj_wh, held, price):
    """Clearing price behind each warehouse: the dearest of its sold units."""
    wp = {w.id: 0.0 for w in net.warehouses}
    for b, k in enumerate(held):
        if k is not None and k != _DUMMY and buyers[b][3] is None:
            wp[obj_wh[k]] = max(wp[obj_wh[k]], price[k])
    return {w: round(v, 6) for w, v in wp.items()}


def _lane_prices(net, buyers, obj_wh, obj_st, held, price):
    """Clearing price per lane slot pool (capped networks only)."""
    lp = {}
    for b, k in enumerate(held):
        if k is not None and k != _DUMMY and buyers[b][3] is None:
            key = f"{obj_wh[k]}->{obj_st[k]}"
            lp[key] = max(lp.get(key, 0.0), price[k])
    return {k: round(v, 6) for k, v in lp.items()}


def _frame(net, buyers, obj_wh, held, price, rnd):
    flow, served = _aggregate_flow(net, buyers, obj_wh, held)
    cost, served_value, elastic = _cost_welfare(net, flow, served)
    real = [(b, k) for b, k in enumerate(held) if buyers[b][3] is None]
    return {
        "round": rnd,
        "flow": {k: round(v, 6) for k, v in flow.items()},
        "assigned": sum(1 for _, k in real if k is not None and k != _DUMMY),
        "unserved": sum(1 for _, k in real if k == _DUMMY),
        "bidding": sum(1 for _, k in real if k is None),
        "cost": round(cost, 4),
        "welfare": round(served_value - cost, 4) if elastic else None,
        "warehousePrice": _warehouse_prices(net, buyers, obj_wh, held, price),
    }


def _result(net, buyers, obj_wh, obj_st, held, price, frames, rounds, eps, capped):
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
        "warehousePrice": _warehouse_prices(net, buyers, obj_wh, held, price),
        "frames": frames,
    }
    if capped:
        out["lanePrice"] = _lane_prices(net, buyers, obj_wh, obj_st, held, price)
    if elastic:
        out["servedValue"] = round(served_value, 6)
        out["lostValue"] = round(sum(s.value * unserved[s.id] for s in elastic), 6)
        out["welfare"] = round(served_value - cost, 6)
    return out
