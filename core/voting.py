"""Social choice: turning ranked ballots into a winner — four ways.

A *profile* is a list of (count, ranking) blocs, where ranking is a tuple of
candidate labels best-to-worst and every ranking lists every candidate. The
four rules:

  * Plurality  - most first-place votes.
  * Borda      - points by rank ((m-1) for 1st down to 0 for last); highest sum.
  * IRV        - instant-runoff: repeatedly eliminate the fewest-first-place
                 candidate and transfer those ballots, until someone has a
                 majority.
  * Condorcet  - the candidate who beats every other head-to-head by majority.
                 May not exist: majorities can cycle (the Condorcet paradox).

Ties are broken deterministically by candidate order so results are reproducible.
"""
from __future__ import annotations

from itertools import combinations
from typing import Dict, List, Optional, Tuple

Ranking = Tuple[str, ...]
Profile = List[Tuple[int, Ranking]]


def _total(profile: Profile) -> int:
    return sum(n for n, _ in profile)


def _tally_first(profile: Profile, active: List[str]) -> Dict[str, int]:
    """First-place counts restricted to the still-active candidates."""
    c = {x: 0 for x in active}
    for n, r in profile:
        for x in r:
            if x in c:
                c[x] += n
                break
    return c


def plurality(profile: Profile, cands: List[str]) -> dict:
    c = _tally_first(profile, cands)
    winner = max(cands, key=lambda x: (c[x], -cands.index(x)))
    return {"winner": winner, "counts": c}


def borda(profile: Profile, cands: List[str]) -> dict:
    m = len(cands)
    s = {x: 0 for x in cands}
    for n, r in profile:
        ranked = [x for x in r if x in s]
        for pos, x in enumerate(ranked):
            s[x] += n * (m - 1 - pos)
    winner = max(cands, key=lambda x: (s[x], -cands.index(x)))
    return {"winner": winner, "scores": s}


def irv(profile: Profile, cands: List[str]) -> dict:
    active = list(cands)
    total = _total(profile)
    rounds = []
    while True:
        c = _tally_first(profile, active)
        leader = max(active, key=lambda x: (c[x], -cands.index(x)))
        rounds.append({"active": list(active), "counts": dict(c),
                       "leader": leader})
        if c[leader] * 2 > total or len(active) == 1:
            return {"winner": leader, "rounds": rounds}
        # eliminate fewest first-place votes (tie-break: later candidate order)
        loser = min(active, key=lambda x: (c[x], -cands.index(x)))
        rounds[-1]["eliminated"] = loser
        active.remove(loser)


def pairwise(profile: Profile, cands: List[str]) -> Dict[str, Dict[str, int]]:
    """Margins: m[a][b] = (voters preferring a to b) - (preferring b to a)."""
    m = {a: {b: 0 for b in cands} for a in cands}
    for a, b in combinations(cands, 2):
        ab = 0
        for n, r in profile:
            ab += n if r.index(a) < r.index(b) else -n
        m[a][b] = ab
        m[b][a] = -ab
    return m


def condorcet(profile: Profile, cands: List[str]) -> dict:
    m = pairwise(profile, cands)
    for a in cands:
        if all(m[a][b] > 0 for b in cands if b != a):
            return {"winner": a, "cycle": False}
    return {"winner": None, "cycle": True}


def evaluate(profile: Profile, cands: List[str]) -> dict:
    total = _total(profile)
    plu, bor, ir, con = (plurality(profile, cands), borda(profile, cands),
                         irv(profile, cands), condorcet(profile, cands))
    winners = {plu["winner"], bor["winner"], ir["winner"]}
    if con["winner"]:
        winners.add(con["winner"])
    return {
        "candidates": cands,
        "totalVoters": total,
        "blocs": [{"count": n, "ranking": list(r),
                   "pct": round(100 * n / total, 1)} for n, r in profile],
        "pairwise": pairwise(profile, cands),
        "results": {
            "plurality": plu,
            "borda": bor,
            "irv": ir,
            "condorcet": con,
        },
        "allAgree": len(winners) == 1,
        "distinctWinners": len(winners),
    }
