"""Smoke tests for the Agora negotiation engine.

Run directly: `python3 tests/test_core.py` (no test framework needed).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analysis import analyse, pareto_frontier, outcome_space
from core.auctions import run_auctions, run_round, first_price_bid
from core.domains import JOB_OFFER, CANDIDATE, EMPLOYER, PROFILES
from core.model import FrequencyModel
from core.protocol import run_session
from core.voting import evaluate as vote_eval
from core.voting_scenarios import SCENARIOS


def check(name, cond):
    assert cond, f"FAILED: {name}"
    print(f"  ok  {name}")


def test_domain_and_utility():
    check("domain enumerates 960 bids", JOB_OFFER.size() == 960)
    check("all_bids matches size", len(JOB_OFFER.all_bids()) == JOB_OFFER.size())
    check("candidate weights sum to 1", abs(sum(CANDIDATE.weights.values()) - 1) < 1e-9)
    check("max bid utility is 1.0", abs(CANDIDATE.utility(CANDIDATE.max_bid()) - 1.0) < 1e-9)
    check("min bid utility is 0.0", abs(CANDIDATE.utility(CANDIDATE.min_bid())) < 1e-9)


def test_frequency_model():
    m = FrequencyModel(JOB_OFFER)
    # feed an opponent that always offers the same value for Salary
    bid = EMPLOYER.max_bid()
    for _ in range(50):
        m.update(bid)
    iw = m.issue_weights()
    check("issue weights normalise to 1", abs(sum(iw.values()) - 1) < 1e-9)
    vw = m.value_weights()
    # the only-ever-offered value should score the maximum (1.0)
    top = bid["Salary"]
    check("most-offered value scores 1.0", abs(vw["Salary"][top] - 1.0) < 1e-9)
    check("estimated utility in range", 0 <= m.estimated_utility(bid) <= 1)


def test_pareto_and_nash():
    g = analyse(JOB_OFFER, CANDIDATE, EMPLOYER)
    check("frontier non-empty", len(g["paretoFrontier"]) > 0)
    # every frontier point is non-dominated in the full outcome space
    pts = outcome_space(JOB_OFFER, CANDIDATE, EMPLOYER)
    front = pareto_frontier(pts)
    dominated = False
    for p in front:
        for q in pts:
            if (q["utilA"] >= p["utilA"] and q["utilB"] >= p["utilB"]
                    and (q["utilA"] > p["utilA"] or q["utilB"] > p["utilB"])):
                dominated = True
    check("no frontier point is dominated", not dominated)
    check("nash point present", "nash" in g and g["nash"]["utilA"] >= 0)


def test_sessions():
    d, ua, ub = PROFILES["job-offer"]
    # v1 vs Conceder should reach a deal; v1 vs Hardliner should not
    deal = run_session(d, ua, ub, "frequency-v1", "conceder", deadline=400)
    check("v1 vs conceder reaches agreement", deal["outcome"]["agreement"])
    nodeal = run_session(d, ua, ub, "frequency-v1", "hardliner", deadline=400)
    check("v1 vs hardliner -> no deal", not nodeal["outcome"]["agreement"])
    # determinism: same seed -> identical outcome
    a = run_session(d, ua, ub, "frequency-v2", "boulware", deadline=400, seed=7)
    b = run_session(d, ua, ub, "frequency-v2", "boulware", deadline=400, seed=7)
    check("runs are deterministic", a["outcome"] == b["outcome"])
    check("trace has model snapshots", len(a["modelTrace"]) > 0)


def test_auctions():
    # single round: winner is highest value; English/Vickrey pay 2nd-highest
    r = run_round([0.2, 0.9, 0.5, 0.1])
    check("highest value wins", r["winner"] == 1)
    check("english pays 2nd-highest value", abs(r["prices"]["english"] - 0.5) < 1e-9)
    check("english == vickrey", r["prices"]["english"] == r["prices"]["vickrey"])
    check("dutch == first-price", r["prices"]["dutch"] == r["prices"]["first-price"])
    check("first-price shades below value",
          r["prices"]["first-price"] < 0.9)
    check("shading formula", abs(first_price_bid(0.9, 4) - 0.9 * 3 / 4) < 1e-9)
    # revenue equivalence: all four means near the theoretical (n-1)/(n+1)
    data = run_auctions(n_bidders=5, n_auctions=4000, seed=1)
    theo = data["summary"]["theoreticalRevenue"]
    check("theoretical revenue = (n-1)/(n+1)", abs(theo - 4 / 6) < 1e-3)
    for m in data["mechanisms"]:
        mean = data["summary"]["perMechanism"][m]["meanRevenue"]
        check(f"{m} mean revenue ~ theoretical", abs(mean - theo) < 0.03)


def test_voting():
    scen = {s["id"]: s for s in SCENARIOS}
    # the Condorcet paradox: a cycle, no Condorcet winner
    cyc = vote_eval(scen["cycle"]["profile"], scen["cycle"]["candidates"])
    check("cycle has no Condorcet winner", cyc["results"]["condorcet"]["winner"] is None)
    check("cycle is flagged", cyc["results"]["condorcet"]["cycle"] is True)
    # the spoiler: plurality differs from the Condorcet winner
    sp = vote_eval(scen["spoiler"]["profile"], scen["spoiler"]["candidates"])
    check("spoiler: plurality picks A", sp["results"]["plurality"]["winner"] == "A")
    check("spoiler: Condorcet picks B", sp["results"]["condorcet"]["winner"] == "B")
    # the showcase: all four rules elect different winners
    ad = vote_eval(scen["alldiffer"]["profile"], scen["alldiffer"]["candidates"])
    check("all-differ has 4 distinct winners", ad["distinctWinners"] == 4)
    w = ad["results"]
    check("all-differ winners P/B/I/C = A/C/D/B",
          [w["plurality"]["winner"], w["borda"]["winner"],
           w["irv"]["winner"], w["condorcet"]["winner"]] == ["A", "C", "D", "B"])
    # pairwise antisymmetry
    pw = cyc["pairwise"]
    check("pairwise margins are antisymmetric",
          all(pw[a][b] == -pw[b][a] for a in pw for b in pw))


if __name__ == "__main__":
    for fn in [test_domain_and_utility, test_frequency_model,
               test_pareto_and_nash, test_sessions, test_auctions, test_voting]:
        print(fn.__name__)
        fn()
    print("\nAll engine smoke tests passed.")
