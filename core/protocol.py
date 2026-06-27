"""Stacked Alternating Offers Protocol (SAOP) session runner.

Agent A and agent B exchange offers in turn until one accepts, one walks away,
or the round deadline is reached. Produces a JSON-serialisable trace with
everything the web demo animates: every offer in (utilA, utilB) space, the
acting agent's model estimate, a downsampled trace of agent A's opponent model,
and the final outcome scored against the Pareto frontier and Nash point.
"""
from __future__ import annotations

from math import hypot
from typing import Optional

from .agents import make_agent
from .analysis import analyse
from .domain import Bid, Domain, UtilitySpace


def run_session(domain: Domain, ua: UtilitySpace, ub: UtilitySpace,
                kind_a: str, kind_b: str, deadline: int = 1000,
                seed: int = 42, snapshot_every: int = 20) -> dict:
    a = make_agent(kind_a, "A", ua, seed)
    b = make_agent(kind_b, "B", ub, seed + 1)
    agents = [a, b]
    uspaces = [ua, ub]

    rounds = []
    model_trace = []
    last_offer: Optional[Bid] = None
    turn = 0           # 0 -> A acts, 1 -> B acts
    agreement = None
    final_round = deadline

    for r in range(deadline + 1):
        t = r / deadline
        actor = agents[turn % 2]
        actor_label = "A" if turn % 2 == 0 else "B"
        action, bid = actor.act(t, last_offer)

        if action == "accept":
            agreement = last_offer
            final_round = r
            rounds.append({"round": r, "t": round(t, 4), "actor": actor_label,
                           "type": "accept"})
            break
        if action == "end":
            final_round = r
            rounds.append({"round": r, "t": round(t, 4), "actor": actor_label,
                           "type": "end"})
            break

        # action == "offer"
        ua_val = ua.utility(bid)
        ub_val = ub.utility(bid)
        est = None
        if getattr(actor, "models_opponent", False):
            est = round(actor.estimated_other(bid), 4)
        rounds.append({
            "round": r, "t": round(t, 4), "actor": actor_label, "type": "offer",
            "bid": bid, "utilA": round(ua_val, 4), "utilB": round(ub_val, 4),
            "estOther": est,
        })

        last_offer = bid
        other = agents[(turn + 1) % 2]
        other.receive(bid)  # opponent observes the offer (model update)

        # snapshot agent A's model of B for the convergence panel
        if r % snapshot_every == 0:
            snap = a.model_snapshot()
            if snap is not None:
                model_trace.append({"round": r, "t": round(t, 4),
                                    "bidsSeen": snap["totalBids"],
                                    "issueWeights": _round_map(snap["issueWeights"])})
        turn += 1
    else:
        final_round = deadline

    geometry = analyse(domain, ua, ub)
    outcome = _score_outcome(agreement, ua, ub, geometry, final_round, deadline)

    return {
        "domain": {
            "name": domain.name,
            "issues": [{"name": n, "values": domain.values[n]}
                       for n in domain.issue_names],
        },
        "agents": {
            "A": {"name": kind_a, "strategy": getattr(a, "strategy", kind_a),
                  "weights": _round_map(ua.weights), "reservation": ua.reservation},
            "B": {"name": kind_b, "strategy": getattr(b, "strategy", kind_b),
                  "weights": _round_map(ub.weights), "reservation": ub.reservation},
        },
        "deadline": deadline,
        "seed": seed,
        "geometry": geometry,
        "rounds": rounds,
        "modelTrace": model_trace,
        "trueWeightsB": _round_map(ub.weights),
        "outcome": outcome,
    }


def _score_outcome(agreement, ua, ub, geometry, final_round, deadline) -> dict:
    if agreement is None:
        return {"agreement": False, "rounds": final_round,
                "utilA": round(ua.reservation, 4), "utilB": round(ub.reservation, 4)}
    a_val, b_val = ua.utility(agreement), ub.utility(agreement)
    on_frontier = any(abs(p["utilA"] - a_val) < 1e-9 and abs(p["utilB"] - b_val) < 1e-9
                      for p in geometry["paretoFrontier"])
    nash = geometry["nash"]
    return {
        "agreement": True, "bid": agreement, "rounds": final_round,
        "utilA": round(a_val, 4), "utilB": round(b_val, 4),
        "paretoOptimal": on_frontier,
        "distToNash": round(hypot(a_val - nash["utilA"], b_val - nash["utilB"]), 4),
    }


def _round_map(m: dict) -> dict:
    return {k: round(v, 4) for k, v in m.items()}
