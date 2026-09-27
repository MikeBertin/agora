"""Smoke tests for the Agora negotiation engine.

Run directly: `python3 tests/test_core.py` (no test framework needed).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analysis import analyse, pareto_frontier, outcome_space
from core.auctions import run_auctions, run_round, first_price_bid
from core.dcop import make_graph, dsa, mgm, count_conflicts
from core.domains import JOB_OFFER, CANDIDATE, EMPLOYER, PROFILES
from core.matching import (all_stable_matchings, best_misreport,
                           blocking_pairs, deferred_acceptance,
                           evaluate as match_eval, random_market)
from core.matching_scenarios import BY_ID as MATCH_BY_ID
from core.matching_scenarios import SCENARIOS as MATCH_SCENARIOS
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


def test_dcop():
    g = make_graph(14, 0.40, 3)
    check("graph is deterministic", make_graph(14, 0.40, 3) == g)
    check("graph has nodes and edges", len(g["nodes"]) == 14 and len(g["edges"]) > 0)
    # with enough colours, both algorithms clear all conflicts on this instance
    fd = dsa(g, 4, 0.7, 60, 1)
    fm = mgm(g, 4, 60, 1)
    check("dsa reduces conflicts", fd[-1]["conflicts"] <= fd[0]["conflicts"])
    check("dsa reaches zero (k=4)", fd[-1]["conflicts"] == 0)
    check("mgm reaches zero (k=4)", fm[-1]["conflicts"] == 0)
    # MGM is monotonic: conflicts never increase round to round
    mono = all(fm[i + 1]["conflicts"] <= fm[i]["conflicts"] for i in range(len(fm) - 1))
    check("mgm is monotonic", mono)
    # too few colours -> cannot reach zero on a dense graph
    dense = make_graph(16, 0.38, 7)
    check("k=2 leaves conflicts on a dense graph",
          dsa(dense, 2, 0.7, 60, 1)[-1]["conflicts"] > 0)
    # count_conflicts agrees with the recorded frame
    last = fd[-1]
    check("count_conflicts matches frame",
          count_conflicts(last["assignment"], g["edges"]) == last["conflicts"])


def test_matching():
    # every scenario, both directions: deferred acceptance lands on a stable
    # matching (no pair would rather elope)
    for s in MATCH_SCENARIOS:
        for d in ("a", "b"):
            run = deferred_acceptance(s["a"], s["b"], d)
            check(f"{s['id']} ({d} proposes) is stable",
                  blocking_pairs(run["matchA"], s["a"], s["b"]) == [])

    # clear: aligned preferences -> a unique stable matching, direction moot
    ev = match_eval(MATCH_BY_ID["clear"]["a"], MATCH_BY_ID["clear"]["b"])
    check("clear has a unique stable matching", ev["stable"]["count"] == 1)
    check("clear: both directions agree",
          ev["runs"]["a"]["matchA"] == ev["runs"]["b"]["matchA"])
    check("clear: the matching is assortative",
          ev["runs"]["a"]["matchA"] == {"Ana": ["Koru"], "Ben": ["Lumen"],
                                        "Cleo": ["Onyx"]})

    # chain: one rejection dominoes through the whole market
    run = deferred_acceptance(MATCH_BY_ID["chain"]["a"],
                              MATCH_BY_ID["chain"]["b"], "a")
    check("chain takes 5 rounds", run["rounds"] == 5)
    check("chain strands Dex", run["matchA"]["Dex"] == []
          and run["unmatchedA"] == ["Dex"])
    check("chain has bump events", sum(len(f["bumped"]) for f in run["frames"]) == 3)
    check("chain: final frame matches the result",
          sorted(map(tuple, run["frames"][-1]["engaged"]))
          == sorted((p, r) for p, rs in run["matchA"].items() for r in rs))

    # direction: proposer-optimal, receiver-pessimal, proved by enumeration
    sc = MATCH_BY_ID["direction"]
    ev = match_eval(sc["a"], sc["b"])
    check("direction has three stable matchings", ev["stable"]["count"] == 3)
    check("candidates proposing: candidates all get their 1st",
          ev["runs"]["a"]["avgRankA"] == 1.0 and ev["runs"]["a"]["avgRankB"] == 3.0)
    check("companies proposing: companies all get their 1st",
          ev["runs"]["b"]["avgRankB"] == 1.0 and ev["runs"]["b"]["avgRankA"] == 3.0)
    da = {p: rs[0] for p, rs in ev["runs"]["a"]["matchA"].items()}
    prefs = sc["a"]["prefs"]
    check("DA is proposer-optimal over every stable matching",
          all(prefs[p].index(da[p]) <= prefs[p].index(m[p])
              for m in ev["stable"]["matchings"] for p in da))

    # strategy: honesty is dominant for proposers only (brute-forced)
    sc = MATCH_BY_ID["strategy"]
    st = match_eval(sc["a"], sc["b"], strategy=True)["strategy"]
    check("no proposer can gain by lying", all(not r["gain"] for r in st["a"]))
    koru = next(r for r in st["b"] if r["agent"] == "Koru")
    check("Koru gains by truncating its list",
          koru["gain"] and koru["best"] == "Ben" and koru["report"] == ["Ben"])

    # hospitals: quotas + the rural hospital theorem, proved by enumeration
    sc = MATCH_BY_ID["hospitals"]
    ev = match_eval(sc["a"], sc["b"])
    check("hospitals has two stable matchings", ev["stable"]["count"] == 2)
    check("Rhea and Sam swap with the direction",
          ev["runs"]["a"]["matchA"]["Rhea"] == ["Metro"]
          and ev["runs"]["b"]["matchA"]["Rhea"] == ["Bay"])
    check("City fills both posts in every stable matching",
          all(sum(1 for r in m.values() if r == "City") == 2
              for m in ev["stable"]["matchings"]))
    check("Rural gets exactly Wren in every stable matching",
          all([p for p, r in m.items() if r == "Rural"] == ["Wren"]
              for m in ev["stable"]["matchings"]))
    check("Vik is unmatched in every stable matching",
          all(m["Vik"] is None for m in ev["stable"]["matchings"]))

    # a random market: still stable, and proposing still helps
    a, b = random_market(6, 3)
    check("random market is deterministic", random_market(6, 3) == (a, b))
    ra = deferred_acceptance(a, b, "a")
    rb = deferred_acceptance(a, b, "b")
    check("random market: both runs stable",
          blocking_pairs(ra["matchA"], a, b) == []
          and blocking_pairs(rb["matchA"], a, b) == [])
    check("random market: proposing side does at least as well",
          ra["avgRankA"] <= rb["avgRankA"] and rb["avgRankB"] <= ra["avgRankB"])
    check("misreport search matches the truthful run",
          best_misreport("C1", "a", a, b)["truthful"] == ra["matchA"]["C1"][0])
    check("full enumeration contains the DA outcome",
          {p: rs[0] for p, rs in ra["matchA"].items()}
          in all_stable_matchings(a, b))


if __name__ == "__main__":
    for fn in [test_domain_and_utility, test_frequency_model,
               test_pareto_and_nash, test_sessions, test_auctions, test_voting,
               test_dcop, test_matching]:
        print(fn.__name__)
        fn()
    print("\nAll engine smoke tests passed.")
