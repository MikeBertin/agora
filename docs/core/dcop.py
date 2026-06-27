"""Distributed constraint optimisation (DCOP) by graph colouring.

Each node is an autonomous agent that must pick one of k colours (read: a time
slot, frequency, or channel). Edges are constraints: two neighbours sharing a
colour is a *conflict* (they clash over the resource). No agent sees the whole
graph — each only knows its own choice and its neighbours' current choices —
yet together they must minimise the global conflict count. This is the
multi-agent backbone of decentralised scheduling and resource allocation.

Two local-search algorithms:

  * DSA (Distributed Stochastic Algorithm) - each round every agent computes
    the colour that minimises its local conflicts and, if that helps, switches
    to it with probability p. Fast and anytime, but p too high causes
    neighbours to "thrash" by moving in lockstep.
  * MGM (Maximum Gain Messaging) - every agent computes its best improvement
    (gain) and tells its neighbours; an agent only moves if its gain is the
    largest in its neighbourhood. Monotonic (never gets worse) but can stall in
    a local optimum.
"""
from __future__ import annotations

import random
from typing import Dict, List, Tuple


def make_graph(n: int, radius: float, seed: int) -> dict:
    """Random geometric graph: nodes in the unit square, edges if close."""
    rng = random.Random(seed)
    nodes = [{"id": i, "x": round(rng.random(), 3), "y": round(rng.random(), 3)}
             for i in range(n)]
    edges = []
    r2 = radius * radius
    for i in range(n):
        for j in range(i + 1, n):
            dx = nodes[i]["x"] - nodes[j]["x"]
            dy = nodes[i]["y"] - nodes[j]["y"]
            if dx * dx + dy * dy <= r2:
                edges.append([i, j])
    return {"nodes": nodes, "edges": edges}


def _adjacency(n: int, edges: List[List[int]]) -> List[List[int]]:
    adj = [[] for _ in range(n)]
    for i, j in edges:
        adj[i].append(j)
        adj[j].append(i)
    return adj


def count_conflicts(assign: List[int], edges: List[List[int]]) -> int:
    return sum(1 for i, j in edges if assign[i] == assign[j])


def _best_color(v: int, assign: List[int], adj: List[List[int]], k: int) -> Tuple[int, int]:
    """Return (best colour for v, gain) given neighbours' current colours."""
    counts = [0] * k
    for u in adj[v]:
        counts[assign[u]] += 1
    cur = counts[assign[v]]
    best = min(range(k), key=lambda c: counts[c])
    return best, cur - counts[best]


def _frame(assign: List[int], edges: List[List[int]], changed: List[int]) -> dict:
    return {"assignment": assign[:], "conflicts": count_conflicts(assign, edges),
            "changed": changed}


def dsa(graph: dict, k: int, p: float, rounds: int, seed: int) -> List[dict]:
    n = len(graph["nodes"])
    edges = graph["edges"]
    adj = _adjacency(n, edges)
    rng = random.Random(seed)
    assign = [rng.randrange(k) for _ in range(n)]
    frames = [_frame(assign, edges, [])]
    for _ in range(rounds):
        new = assign[:]
        changed = []
        for v in range(n):
            bc, gain = _best_color(v, assign, adj, k)
            if gain > 0 and bc != assign[v] and rng.random() < p:
                new[v] = bc
                changed.append(v)
        assign = new
        frames.append(_frame(assign, edges, changed))
    return frames


def mgm(graph: dict, k: int, rounds: int, seed: int) -> List[dict]:
    n = len(graph["nodes"])
    edges = graph["edges"]
    adj = _adjacency(n, edges)
    rng = random.Random(seed)
    assign = [rng.randrange(k) for _ in range(n)]
    frames = [_frame(assign, edges, [])]
    for _ in range(rounds):
        proposals = [_best_color(v, assign, adj, k) for v in range(n)]
        new = assign[:]
        changed = []
        for v in range(n):
            bc, gain = proposals[v]
            if gain <= 0:
                continue
            # move only if strictly the best gain locally (ties: lowest id wins)
            wins = all(gain > proposals[u][1] or (gain == proposals[u][1] and v < u)
                       for u in adj[v])
            if wins:
                new[v] = bc
                changed.append(v)
        assign = new
        frames.append(_frame(assign, edges, changed))
    return frames


def solve(graph: dict, k: int, algo: str, p: float, rounds: int, seed: int) -> dict:
    """Run one algorithm and also both conflict curves for comparison."""
    runs = {
        "dsa": dsa(graph, k, p, rounds, seed),
        "mgm": mgm(graph, k, rounds, seed),
    }
    frames = runs[algo]
    return {
        "graph": graph, "k": k, "algo": algo, "p": p, "rounds": rounds, "seed": seed,
        "frames": frames,
        "convergence": {a: [f["conflicts"] for f in fr] for a, fr in runs.items()},
        "edgeCount": len(graph["edges"]),
        "finalConflicts": frames[-1]["conflicts"],
    }
