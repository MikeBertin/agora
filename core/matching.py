"""Stable matching: Gale-Shapley deferred acceptance, run from either side.

A two-sided market: candidates and companies (or residents and hospitals),
each ranking a subset of the other side; an agent may take several partners
(a capacity, or quota). A matching is *stable* when no candidate-company pair
would rather drop their assigned partners for each other.

Deferred acceptance, round-synchronous so the demo can animate it: every
under-matched proposer proposes to the best partners it hasn't yet tried;
every receiver *tentatively* holds the best offers up to its quota and rejects
the rest, bumping anyone it was holding for a better arrival; repeat until no
proposer has anywhere left to propose. The result (Gale & Shapley 1962) is
stable and **proposer-optimal**: each proposer gets the best partner it has in
ANY stable matching, and each receiver its worst, so which side proposes
decides who the market favours. Truth-telling is a dominant strategy for the
proposing side only; a receiver can sometimes gain by shortening its list.

The markets here are small enough to *prove* those claims per instance rather
than assert them: ``all_stable_matchings`` enumerates every stable matching
and ``best_misreport`` brute-forces every ordered sublist an agent could
report. A side is a plain dict ``{"label", "prefs", "caps"?}`` (caps default
to 1) and every result is JSON-serialisable for the web demo. Pairs in frames
and matches are always ordered (side-a agent, side-b agent), whichever side
proposed.
"""
from __future__ import annotations

import random
from itertools import permutations
from typing import Dict, List, Optional, Tuple

Prefs = Dict[str, List[str]]


def _caps(side: dict) -> Dict[str, int]:
    caps = side.get("caps") or {}
    return {x: int(caps.get(x, 1)) for x in side["prefs"]}


def _rank(prefs: Prefs, agent: str, partner: str) -> int:
    """1-based rank of ``partner`` on ``agent``'s list."""
    return prefs[agent].index(partner) + 1


def _da(prop_prefs: Prefs, recv_prefs: Prefs,
        prop_caps: Dict[str, int], recv_caps: Dict[str, int]):
    """The raw algorithm; pairs in frames are (proposer, receiver)."""
    rrank = {r: {p: i for i, p in enumerate(ps)} for r, ps in recv_prefs.items()}
    nxt = {p: 0 for p in prop_prefs}          # next untried index per proposer
    holds = {p: [] for p in prop_prefs}       # proposer -> receivers holding it
    engaged = {r: [] for r in recv_prefs}     # receiver -> proposers held
    frames: List[dict] = []
    rounds = n_proposals = 0

    while True:
        proposals: List[Tuple[str, str]] = []
        for p, lst in prop_prefs.items():
            want = prop_caps[p] - len(holds[p])
            while want > 0 and nxt[p] < len(lst):
                proposals.append((p, lst[nxt[p]]))
                nxt[p] += 1
                want -= 1
        if not proposals:
            break
        rounds += 1
        n_proposals += len(proposals)

        accepted, rejected, bumped = [], [], []
        by_r: Dict[str, List[str]] = {}
        for p, r in proposals:
            by_r.setdefault(r, []).append(p)
        for r, cands in by_r.items():
            ok = [p for p in cands if p in rrank[r]]
            rejected += [(p, r) for p in cands if p not in rrank[r]]
            pool = sorted(set(engaged[r]) | set(ok), key=lambda p: rrank[r][p])
            keep = pool[:recv_caps[r]]
            for p in pool[recv_caps[r]:]:
                if p in engaged[r]:
                    holds[p].remove(r)
                    bumped.append((p, r))
                else:
                    rejected.append((p, r))
            for p in keep:
                if p not in engaged[r]:
                    holds[p].append(r)
                    accepted.append((p, r))
            engaged[r] = keep

        frames.append({
            "round": rounds,
            "proposals": proposals,
            "accepted": accepted, "rejected": rejected, "bumped": bumped,
            "engaged": [(p, r) for r in recv_prefs for p in engaged[r]],
        })
    return holds, engaged, frames, rounds, n_proposals


def deferred_acceptance(a: dict, b: dict, proposing: str = "a") -> dict:
    """Run deferred acceptance with side ``proposing`` making the offers.

    Returns matches, per-agent ranks and playback frames, normalised so pairs
    are always (side-a agent, side-b agent) whichever side proposed.
    """
    a_caps, b_caps = _caps(a), _caps(b)
    if proposing == "a":
        holds, engaged, frames, rounds, n = _da(a["prefs"], b["prefs"],
                                                a_caps, b_caps)
        match_a, match_b = holds, engaged
        flip = False
    elif proposing == "b":
        holds, engaged, frames, rounds, n = _da(b["prefs"], a["prefs"],
                                                b_caps, a_caps)
        match_a, match_b = engaged, holds
        flip = True
    else:
        raise ValueError(f"proposing must be 'a' or 'b', not {proposing!r}")

    if flip:
        def norm(pairs):
            return [[y, x] for x, y in pairs]
        frames = [{**f, **{k: norm(f[k]) for k in
                           ("proposals", "accepted", "rejected", "bumped",
                            "engaged")}} for f in frames]
    else:
        frames = [{**f, **{k: [list(t) for t in f[k]] for k in
                           ("proposals", "accepted", "rejected", "bumped",
                            "engaged")}} for f in frames]

    match_a = {p: sorted(rs, key=lambda r: a["prefs"][p].index(r))
               for p, rs in match_a.items()}
    match_b = {r: sorted(ps, key=lambda p: b["prefs"][r].index(p))
               for r, ps in match_b.items()}
    rank_a = {p: [_rank(a["prefs"], p, r) for r in rs]
              for p, rs in match_a.items()}
    rank_b = {r: [_rank(b["prefs"], r, p) for p in ps]
              for r, ps in match_b.items()}

    def avg(ranks):
        flat = [x for v in ranks.values() for x in v]
        return round(sum(flat) / len(flat), 3) if flat else None

    return {
        "proposing": proposing, "rounds": rounds, "proposals": n,
        "frames": frames,
        "matchA": match_a, "matchB": match_b,
        "rankA": rank_a, "rankB": rank_b,
        "avgRankA": avg(rank_a), "avgRankB": avg(rank_b),
        "unmatchedA": [p for p in a["prefs"] if not match_a[p]],
        "unmatchedB": [r for r in b["prefs"] if not match_b[r]],
    }


def blocking_pairs(match_a: Dict[str, List[str]], a: dict, b: dict) -> list:
    """All (a-agent, b-agent) pairs that would jointly abandon the matching."""
    a_caps, b_caps = _caps(a), _caps(b)
    match_b: Dict[str, List[str]] = {r: [] for r in b["prefs"]}
    for p, rs in match_a.items():
        for r in rs:
            match_b[r].append(p)
    out = []
    for p, plist in a["prefs"].items():
        cur = match_a.get(p, [])
        worst_p = max((_rank(a["prefs"], p, r) for r in cur), default=None)
        for r in plist:
            if r in cur or p not in b["prefs"].get(r, []):
                continue
            p_wants = len(cur) < a_caps[p] or _rank(a["prefs"], p, r) < worst_p
            held = match_b[r]
            worst_r = max((_rank(b["prefs"], r, q) for q in held), default=None)
            r_wants = len(held) < b_caps[r] or _rank(b["prefs"], r, p) < worst_r
            if p_wants and r_wants:
                out.append((p, r))
    return out


def all_stable_matchings(a: dict, b: dict) -> List[Dict[str, Optional[str]]]:
    """Every stable matching, by brute force (side-a capacities must be 1).

    Small markets only: enumerates all individually-rational assignments of
    each a-agent to an acceptable partner (or none) within b's quotas.
    """
    a_caps, b_caps = _caps(a), _caps(b)
    assert all(c == 1 for c in a_caps.values()), \
        "enumeration assumes unit capacity on side a"
    agents = list(a["prefs"])
    mutual = {p: [r for r in a["prefs"][p] if p in b["prefs"].get(r, [])]
              for p in agents}
    out: List[Dict[str, Optional[str]]] = []
    load = {r: 0 for r in b["prefs"]}
    cur: Dict[str, Optional[str]] = {}

    def rec(i: int) -> None:
        if i == len(agents):
            match_a = {p: ([r] if r else []) for p, r in cur.items()}
            if not blocking_pairs(match_a, a, b):
                out.append(dict(cur))
            return
        p = agents[i]
        for r in mutual[p] + [None]:
            if r is not None and load[r] >= b_caps[r]:
                continue
            cur[p] = r
            if r:
                load[r] += 1
            rec(i + 1)
            if r:
                load[r] -= 1

    rec(0)
    return out


def best_misreport(agent: str, side: str, a: dict, b: dict) -> dict:
    """Brute-force every list ``agent`` could report (side a proposing).

    Tries every ordered sublist of the agent's true preferences, reruns the
    market, and scores the agent's partner by its TRUE list. ``gain`` is True
    when some lie beats honesty: never for a proposer (strategy-proofness),
    sometimes for a receiver. Assumes the agent has capacity 1.
    """
    side_d = a if side == "a" else b
    true_list = side_d["prefs"][agent]

    def outcome(res: dict) -> Optional[str]:
        m = (res["matchA"] if side == "a" else res["matchB"])[agent]
        return m[0] if m else None

    def score(partner: Optional[str]) -> int:  # lower is better
        return true_list.index(partner) if partner in true_list \
            else len(true_list)

    truthful = outcome(deferred_acceptance(a, b, "a"))
    best, best_report = truthful, None
    for k in range(1, len(true_list) + 1):
        for rep in permutations(true_list, k):
            trial = {"prefs": dict(side_d["prefs"]), "caps": side_d.get("caps")}
            trial["prefs"][agent] = list(rep)
            res = deferred_acceptance(trial if side == "a" else a,
                                      trial if side == "b" else b, "a")
            got = outcome(res)
            if score(got) < score(best):
                best, best_report = got, list(rep)
    return {"agent": agent, "side": side, "truthful": truthful,
            "best": best, "report": best_report,
            "gain": best_report is not None}


def evaluate(a: dict, b: dict, stable: bool = True,
             strategy: bool = False) -> dict:
    """The full demo payload for one market: both directions, and proofs.

    Runs deferred acceptance with each side proposing; optionally enumerates
    every stable matching and brute-forces every agent's possible misreports.
    """
    out = {
        "sides": {
            "a": {"label": a["label"], "agents": list(a["prefs"]),
                  "prefs": a["prefs"], "caps": _caps(a)},
            "b": {"label": b["label"], "agents": list(b["prefs"]),
                  "prefs": b["prefs"], "caps": _caps(b)},
        },
        "runs": {"a": deferred_acceptance(a, b, "a"),
                 "b": deferred_acceptance(a, b, "b")},
    }
    if stable:
        ms = all_stable_matchings(a, b)
        out["stable"] = {"count": len(ms), "matchings": ms}
    if strategy:
        out["strategy"] = {
            "a": [best_misreport(p, "a", a, b) for p in a["prefs"]],
            "b": [best_misreport(r, "b", a, b) for r in b["prefs"]],
        }
    return out


def random_market(n: int, seed: int) -> Tuple[dict, dict]:
    """A one-to-one market with full random lists, deterministic per seed."""
    rng = random.Random(seed)
    cands = [f"C{i+1}" for i in range(n)]
    firms = [f"F{i+1}" for i in range(n)]
    a = {"label": "Candidates",
         "prefs": {c: rng.sample(firms, n) for c in cands}}
    b = {"label": "Companies",
         "prefs": {f: rng.sample(cands, n) for f in firms}}
    return a, b
