"""The market at scale: sequential bidding with epsilon-scaling.

``market.py`` bids synchronously (every free buyer at once) because that is
the honest decentralised story and it yields playback frames. The price of that
story is speed: synchronous bidding is provably incompatible with ε-scaling
(large-ε phases mis-assign under stale prices; tried and reverted), so it must
run its whole price war at the final tiny ε and the round count grows with the
price range. Fine for the demo's hand-sized instances, hopeless at scale.

This module is the fast variant: **Gauss–Seidel bidding** (one buyer at a time,
prices always fresh) with **ε-scaling**: run the auction at a coarse ε, keep
the prices, quarter ε and rerun, down to the final ε < 1/n that guarantees
optimality for integer benefits. Near-equilibrium prices from each phase make
the next phase cheap; this is Bertsekas' classic recipe.

Scaling is only provably clean when every person ends up matched, so the
assignment is *balanced* first:

  * an elastic buyer's outside option ("stay unserved") becomes a real object:
    a personal slot worth 0 that only that buyer may take; and
  * **dummy buyers**, indifferent among *all* objects (benefit 0), absorb
    whatever real demand leaves unsold, whether spare capacity or an untaken outside
    slot. (They must not be capacity-only: a perfect matching would then force
    them to evict every elastic buyer.)

Every person then bids until matched, no one leaves the market, and the forward
auction's ε-scaling guarantees apply directly. One honest caveat: prices carried
across phases end up uniformly shifted, so unlike the synchronous variant this
one guarantees the optimal *allocation* but not price-equals-rent; the dual
discovery story belongs to ``market.py``. The disaggregation (unit buyers,
unit objects, per-lane slot pools + phantom buyers when lanes are capped) is
shared with ``market.py``, so both variants solve literally the same assignment
problem. Bidding rows are numpy-vectorised; thousands of units are fine.

No playback frames: this variant exists for the scale benchmark
(``experiments/bench_supply.py``), not the demo.
"""
from __future__ import annotations

from collections import deque

import numpy as np

from .market import (_DUMMY, _big_value, _disaggregate, _infeasible, _result,
                     _validate_units)
from .model import Network

_MAX_BIDS = 5_000_000  # hard safety net; never hit on feasible instances


def solve_market_scaled(net: Network, theta: float = 4.0) -> dict:
    """Run the ε-scaled sequential auction to the optimum; no frames.

    Returns the same result shape as ``solve_market`` (method
    ``"market-scaled"``, empty ``frames``) plus ``phases`` and ``bids``.
    """
    _validate_units(net)
    buyers, obj_wh, obj_st, slots_to, capped = _disaggregate(net)
    nB, nK = len(buyers), len(obj_wh)
    eps_final = 1.0 / (nB + 1)

    if _infeasible(net, slots_to):
        out = _result(net, buyers, obj_wh, obj_st,
                      [None] * nB, [0.0] * nK, [], 0, eps_final, capped)
        out.update(method="market-scaled", phases=0, bids=0)
        return out

    # --- balance the assignment: outside-option objects + dummy buyers -----
    elastic_b = [b for b, (_, _, mand, ph) in enumerate(buyers)
                 if ph is None and not mand]
    nE = len(elastic_b)
    nO = nK + nE                       # objects: capacity, then outsides
    nD = max(0, nO - nB)               # dummies absorb unsold capacity
    nP = nB + nD                       # persons: buyers, then dummies

    # --- benefit matrix, one row per person (rows shared per store) --------
    big = _big_value(net)
    wh_cost = np.array([net.warehouse(w).cost for w in obj_wh])
    srow = {}                          # store id -> benefit over capacity objects
    for s in net.stores:
        row = np.full(nK, -np.inf)
        for k in range(nK):
            if obj_st[k] is not None and obj_st[k] != s.id:
                continue
            lane = net.lane(obj_wh[k], s.id)
            if lane is not None:
                row[k] = -wh_cost[k] - lane.cost
        srow[s.id] = row

    A = np.full((nP, nO), -np.inf)
    obj_wh_arr = np.array(obj_wh)
    for b, (sid, val, mand, ph) in enumerate(buyers):
        if ph is not None:             # phantom: any slot of its own warehouse
            A[b, :nK] = np.where(obj_wh_arr == ph, 0.0, -np.inf)
        else:
            A[b, :nK] = (big if mand else val) + srow[sid]
    for j, b in enumerate(elastic_b):  # personal outside slots, worth 0
        A[b, nK + j] = 0.0
    # Dummies take whatever is left over, capacity or an untaken outside
    # slot. Restricting them to capacity would force them to *evict* elastic
    # buyers (a perfect matching would need every capacity object dummied).
    A[nB:, :] = 0.0

    # --- ε-scaling: phases of a Gauss–Seidel auction, prices carried over --
    price = np.zeros(nO)
    owner = np.full(nO, -1, dtype=int)
    spread = float(np.max(A[np.isfinite(A)])) - \
        float(min(0.0, np.min(A[np.isfinite(A)])))
    eps = max(eps_final, spread / 4.0)
    phases = bids = 0

    while True:
        phases += 1
        owner[:] = -1                  # fresh assignment, seasoned prices
        free = deque(range(nP))
        while free and bids < _MAX_BIDS:
            b = free.popleft()
            net_v = A[b] - price
            k = int(np.argmax(net_v))
            best = net_v[k]
            if best == -np.inf:
                continue               # unmatchable (infeasible instance)
            net_v[k] = -np.inf
            second = float(np.max(net_v))
            if second == -np.inf:
                second = best          # sole option: minimal raise
            price[k] = A[b, k] - second + eps
            if owner[k] >= 0:
                free.append(owner[k])
            owner[k] = b
            bids += 1
        if eps <= eps_final or bids >= _MAX_BIDS:
            break
        eps = max(eps_final, eps / theta)

    # --- fold back to the shared result shape ------------------------------
    held = [None] * nB
    for k in range(nK):
        if 0 <= owner[k] < nB:
            held[owner[k]] = k
    for j, b in enumerate(elastic_b):
        if owner[nK + j] == b:
            held[b] = _DUMMY
    out = _result(net, buyers, obj_wh, obj_st, held,
                  [float(p) for p in price[:nK]], [], bids, eps, capped)
    out.update(method="market-scaled", phases=phases, bids=bids)
    return out
