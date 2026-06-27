"""Single-item auctions under independent private values (IPV).

Four classic mechanisms, each with its game-theoretic equilibrium strategy:

  * English  (ascending clock)  - truthful; stay in until the price reaches
                                  your value. Winner pays the 2nd-highest value.
  * Vickrey  (2nd-price sealed) - truthful is a dominant strategy. Same outcome
                                  as English: winner pays the 2nd-highest value.
  * First-price (sealed)        - bidding your value wins you zero surplus, so
                                  the symmetric equilibrium shades the bid to
                                  b(v) = v·(n-1)/n. Winner pays their own bid.
  * Dutch    (descending clock) - strategically equivalent to first-price; the
                                  bidder plans to accept at b(v) = v·(n-1)/n.

For values drawn uniformly on [0,1] all four have the same expected revenue,
(n-1)/(n+1) — the revenue-equivalence theorem — and all four are efficient
(the highest-value bidder always wins).
"""
from __future__ import annotations

import random
from typing import Dict, List

MECHANISMS = ["english", "vickrey", "first-price", "dutch"]
MECH_LABELS = {
    "english": "English (ascending)",
    "vickrey": "Vickrey (2nd-price)",
    "first-price": "First-price (sealed)",
    "dutch": "Dutch (descending)",
}


def first_price_bid(value: float, n: int) -> float:
    """Symmetric Bayes-Nash equilibrium bid for IPV uniform[0,1]."""
    return value * (n - 1) / n


def run_round(values: List[float]) -> dict:
    """Resolve a single auction (same private values) under all mechanisms."""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i], reverse=True)
    hi, second = order[0], order[1]
    v_hi, v_2nd = values[hi], values[second]
    bids_fp = [first_price_bid(v, n) for v in values]
    price_fp = bids_fp[hi]  # highest value -> highest bid (monotonic)
    return {
        "values": [round(v, 4) for v in values],
        "bidsFP": [round(b, 4) for b in bids_fp],
        "winner": hi,                       # identical across mechanisms (efficient)
        "prices": {
            "english": round(v_2nd, 4),
            "vickrey": round(v_2nd, 4),
            "first-price": round(price_fp, 4),
            "dutch": round(price_fp, 4),
        },
    }


def run_auctions(n_bidders: int = 5, n_auctions: int = 800, seed: int = 42) -> dict:
    rng = random.Random(seed)
    rounds = []
    totals = {m: 0.0 for m in MECHANISMS}
    for _ in range(n_auctions):
        values = [rng.random() for _ in range(n_bidders)]
        r = run_round(values)
        rounds.append(r)
        for m in MECHANISMS:
            totals[m] += r["prices"][m]

    theoretical = (n_bidders - 1) / (n_bidders + 1)
    summary = {
        "perMechanism": {
            m: {"meanRevenue": round(totals[m] / n_auctions, 4),
                "label": MECH_LABELS[m]}
            for m in MECHANISMS
        },
        "theoreticalRevenue": round(theoretical, 4),
        "efficiency": 1.0,  # highest-value bidder always wins, by construction
    }
    return {
        "config": {"nBidders": n_bidders, "nAuctions": n_auctions,
                   "distribution": "uniform[0,1]", "seed": seed},
        "mechanisms": MECHANISMS,
        "mechLabels": MECH_LABELS,
        "rounds": rounds,
        "summary": summary,
    }
