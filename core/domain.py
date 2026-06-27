"""Discrete multi-issue domains and additive utility spaces.

A Bid is a plain dict mapping issue name -> chosen value (both strings), the
same shape GENIUS uses for a discrete `AdditiveUtilitySpace`.
"""
from __future__ import annotations

from itertools import product
from typing import Dict, List


Bid = Dict[str, str]


class Domain:
    """An ordered list of issues, each with a list of discrete values."""

    def __init__(self, name: str, issues: List[tuple]):
        # issues: list of (issue_name, [value, ...])
        self.name = name
        self.issue_names = [n for n, _ in issues]
        self.values = {n: list(vs) for n, vs in issues}

    def all_bids(self) -> List[Bid]:
        """Enumerate every possible bid (the domain is small by design)."""
        names = self.issue_names
        return [
            dict(zip(names, combo))
            for combo in product(*(self.values[n] for n in names))
        ]

    def size(self) -> int:
        n = 1
        for vs in self.values.values():
            n *= len(vs)
        return n


class UtilitySpace:
    """Additive utility: U(bid) = sum_i weight_i * eval_i(value_i).

    weights sum to 1; evals give each value a score in [0, 1].
    """

    def __init__(self, domain: Domain, weights: Dict[str, float],
                 evals: Dict[str, Dict[str, float]], reservation: float = 0.0):
        self.domain = domain
        total = sum(weights.values())
        self.weights = {k: v / total for k, v in weights.items()}  # normalise
        self.evals = evals
        self.reservation = reservation

    def utility(self, bid: Bid) -> float:
        return sum(self.weights[i] * self.evals[i][bid[i]]
                   for i in self.domain.issue_names)

    def max_bid(self) -> Bid:
        return {i: max(self.evals[i], key=self.evals[i].get)
                for i in self.domain.issue_names}

    def min_bid(self) -> Bid:
        return {i: min(self.evals[i], key=self.evals[i].get)
                for i in self.domain.issue_names}
