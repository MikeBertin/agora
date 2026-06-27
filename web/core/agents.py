"""Negotiation agents for the SAOP protocol.

Every agent exposes:
  * receive(bid)        - observe an offer from the opponent (model update)
  * act(t, last_offer)  - return an Action given normalised time t in [0,1]

Action is ("offer", bid) | ("accept", None) | ("end", None).

Two flagship agents port the COMP6203 coursework agent:
  * FrequencyAgentV1 - faithful: fixed 0.8 target, accepts only at the buzzer.
  * FrequencyAgentV2 - improved: time-dependent concession + AC_next acceptance.
Both share the frequency opponent model and the Pareto-seeking bid choice
(among bids good enough for us, offer the one the model thinks is best for
the opponent).
"""
from __future__ import annotations

import random
from typing import List, Optional, Tuple

from .domain import Bid, UtilitySpace
from .model import FrequencyModel

Action = Tuple[str, Optional[Bid]]


class Agent:
    strategy = "base"
    models_opponent = False

    def __init__(self, name: str, util_space: UtilitySpace, seed: int = 0):
        self.name = name
        self.u = util_space
        self.domain = util_space.domain
        self.names = self.domain.issue_names
        self.rng = random.Random(seed)
        # bids sorted by our own utility, descending (lets us stop early)
        self.bids_by_util: List[Tuple[Bid, float]] = sorted(
            ((b, self.u.utility(b)) for b in self.domain.all_bids()),
            key=lambda bu: bu[1], reverse=True,
        )
        self.max_util = self.bids_by_util[0][1]

    def receive(self, bid: Bid) -> None:
        pass

    def target(self, t: float) -> float:
        return 0.8

    def propose(self, t: float) -> Bid:
        """Best bid for us at or above target; ties broken in our favour."""
        tgt = self.target(t)
        for bid, util in self.bids_by_util:
            if util >= tgt:
                return bid
        return self.bids_by_util[0][0]  # nothing clears the bar -> our best

    def act(self, t: float, last_offer: Optional[Bid]) -> Action:
        raise NotImplementedError

    def model_snapshot(self):
        return None


# ----------------------------------------------------------------------------
# Frequency agents (the coursework port)
# ----------------------------------------------------------------------------
class _FrequencyAgent(Agent):
    models_opponent = True

    def __init__(self, name: str, util_space: UtilitySpace, seed: int = 0):
        super().__init__(name, util_space, seed)
        self.model = FrequencyModel(self.domain)

    def receive(self, bid: Bid) -> None:
        self.model.update(bid)

    def propose(self, t: float) -> Bid:
        """Among bids at/above target, pick the one best for the opponent."""
        tgt = self.target(t)
        iw = self.model.issue_weights()
        vw = self.model.value_weights()
        best: Optional[Bid] = None
        best_score = -1.0
        for bid, util in self.bids_by_util:
            if util < tgt:
                break  # sorted desc: no further bid clears the target
            score = sum(iw[i] * vw[i][bid[i]] for i in self.names)
            if score > best_score:
                best_score, best = score, bid
        return best if best is not None else self.bids_by_util[0][0]

    def estimated_other(self, bid: Bid) -> float:
        return self.model.estimated_utility(bid)

    def model_snapshot(self):
        return self.model.snapshot()


class FrequencyAgentV1(_FrequencyAgent):
    """Faithful coursework agent: fixed target, accept only near the deadline."""
    strategy = "frequency-v1"

    def target(self, t: float) -> float:
        return 0.8

    def act(self, t: float, last_offer: Optional[Bid]) -> Action:
        if t >= 0.99 and last_offer is not None:
            if self.u.utility(last_offer) >= self.u.reservation:
                return ("accept", None)
            return ("end", None)
        return ("offer", self.propose(t))


class FrequencyAgentV2(_FrequencyAgent):
    """Improved agent: Boulware concession + AC_next acceptance."""
    strategy = "frequency-v2"
    floor = 0.6
    e = 0.15

    def target(self, t: float) -> float:
        return self.floor + (1.0 - self.floor) * (1.0 - t ** (1.0 / self.e))

    def act(self, t: float, last_offer: Optional[Bid]) -> Action:
        if last_offer is not None:
            u_last = self.u.utility(last_offer)
            my_next = self.propose(t)
            # AC_next: accept if their offer beats what we'd counter with,
            # or already clears our (conceding) target.
            if u_last >= self.u.utility(my_next) or u_last >= self.target(t):
                return ("accept", None)
            if t >= 0.99:  # buzzer: take anything above reservation
                if u_last >= self.u.reservation:
                    return ("accept", None)
                return ("end", None)
            return ("offer", my_next)
        return ("offer", self.propose(t))


# ----------------------------------------------------------------------------
# Opponents
# ----------------------------------------------------------------------------
class TimeDependentAgent(Agent):
    """Boulware (e<1, tough) / Conceder (e>1, fast) time-dependent tactic."""

    def __init__(self, name: str, util_space: UtilitySpace, e: float,
                 strategy: str, seed: int = 0):
        super().__init__(name, util_space, seed)
        self.e = e
        self.strategy = strategy

    def target(self, t: float) -> float:
        floor = self.u.reservation
        return floor + (self.max_util - floor) * (1.0 - t ** (1.0 / self.e))

    def propose(self, t: float) -> Bid:
        tgt = self.target(t)
        # offer somewhere along the current iso-utility band (adds variety)
        band = [b for b, u in self.bids_by_util if tgt <= u <= tgt + 0.1]
        if not band:
            band = [b for b, u in self.bids_by_util if u >= tgt]
        if not band:
            return self.bids_by_util[0][0]
        return self.rng.choice(band)

    def act(self, t: float, last_offer: Optional[Bid]) -> Action:
        if last_offer is not None and self.u.utility(last_offer) >= self.target(t):
            return ("accept", None)
        if t >= 0.99 and last_offer is not None and \
                self.u.utility(last_offer) >= self.u.reservation:
            return ("accept", None)
        return ("offer", self.propose(t))


class Hardliner(Agent):
    """Repeats its maximum bid forever; effectively never concedes."""
    strategy = "hardliner"

    def act(self, t: float, last_offer: Optional[Bid]) -> Action:
        if last_offer is not None and self.u.utility(last_offer) >= 0.99 * self.max_util:
            return ("accept", None)
        return ("offer", self.bids_by_util[0][0])


class RandomAboveTarget(Agent):
    """The original example agent: random bids above a fixed target."""
    strategy = "random"

    def target(self, t: float) -> float:
        return 0.8

    def propose(self, t: float) -> Bid:
        band = [b for b, u in self.bids_by_util if u >= 0.8]
        return self.rng.choice(band) if band else self.bids_by_util[0][0]

    def act(self, t: float, last_offer: Optional[Bid]) -> Action:
        if last_offer is not None and self.u.utility(last_offer) >= 0.8:
            return ("accept", None)
        return ("offer", self.propose(t))


def make_agent(kind: str, name: str, util_space: UtilitySpace, seed: int = 0) -> Agent:
    if kind == "frequency-v1":
        return FrequencyAgentV1(name, util_space, seed)
    if kind == "frequency-v2":
        return FrequencyAgentV2(name, util_space, seed)
    if kind == "boulware":
        return TimeDependentAgent(name, util_space, e=0.2, strategy="boulware", seed=seed)
    if kind == "conceder":
        return TimeDependentAgent(name, util_space, e=2.0, strategy="conceder", seed=seed)
    if kind == "hardliner":
        return Hardliner(name, util_space, seed)
    if kind == "random":
        return RandomAboveTarget(name, util_space, seed)
    raise ValueError(f"unknown agent kind: {kind}")


AGENT_KINDS = ["frequency-v1", "frequency-v2", "boulware", "conceder", "hardliner", "random"]
