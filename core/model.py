"""Frequency-based opponent model.

Faithful port of the model in the COMP6203 coursework agent (group2.MyAgent):

  * Per issue, count how often the opponent offers each value.
  * Estimate each value's utility to the opponent by its frequency RANK:
    the most-offered value scores 1.0, the least-offered scores 1/n
    (formula (n - rank + 1)/n, exactly as the original).
  * Estimate each issue's WEIGHT by how concentrated the opponent's offers
    are on that issue: w_i = sum(freq^2) / total^2, then normalised across
    issues. An opponent who always picks the same value for an issue reveals
    that issue matters to them.

The original incremented a `totalPriorBids` counter once per (issue, value);
because the issue weights are normalised across issues that constant cancels
out, so the cleaned-up counting here gives identical weights.
"""
from __future__ import annotations

from typing import Dict, List

from .domain import Bid, Domain


class FrequencyModel:
    def __init__(self, domain: Domain):
        self.domain = domain
        self.counts: Dict[str, Dict[str, int]] = {
            i: {v: 0 for v in domain.values[i]} for i in domain.issue_names
        }
        self.total_bids = 0

    def update(self, bid: Bid) -> None:
        """Record one offer received from the opponent."""
        for issue in self.domain.issue_names:
            self.counts[issue][bid[issue]] += 1
        self.total_bids += 1

    def value_weights(self) -> Dict[str, Dict[str, float]]:
        """Estimated per-value utility to the opponent, in [1/n, 1]."""
        out: Dict[str, Dict[str, float]] = {}
        for issue in self.domain.issue_names:
            counts = self.counts[issue]
            n = len(counts)
            # rank values by frequency, ascending (least -> most offered)
            ranked = sorted(counts, key=lambda v: counts[v])
            out[issue] = {v: (rank + 1) / n for rank, v in enumerate(ranked)}
        return out

    def issue_weights(self) -> Dict[str, float]:
        """Estimated per-issue weight from offer concentration, normalised."""
        raw: Dict[str, float] = {}
        for issue in self.domain.issue_names:
            counts = self.counts[issue]
            total = sum(counts.values())
            if total == 0:
                raw[issue] = 0.0
            else:
                raw[issue] = sum(c * c for c in counts.values()) / (total * total)
        s = sum(raw.values())
        if s == 0:  # nothing seen yet -> uniform
            n = len(raw)
            return {i: 1.0 / n for i in raw}
        return {i: w / s for i, w in raw.items()}

    def estimated_utility(self, bid: Bid) -> float:
        """Our estimate of the opponent's utility for `bid`."""
        if self.total_bids == 0:
            return 0.0
        iw = self.issue_weights()
        vw = self.value_weights()
        return sum(iw[i] * vw[i][bid[i]] for i in self.domain.issue_names)

    def snapshot(self) -> dict:
        """Compact model state for the convergence panel."""
        return {
            "issueWeights": self.issue_weights(),
            "valueWeights": self.value_weights(),
            "totalBids": self.total_bids,
        }
