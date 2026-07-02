"""Smoke tests for the Agora supply engine.

Needs scipy, so run under the project venv:
  .venv/bin/python tests/test_supply.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supply.analysis import compare, evaluate
from supply.greedy import solve_greedy
from supply.instances import (SCENARIOS, bottleneck, myopia, regions,
                              shortage, stranded)
from supply.market import solve_market, _downsample
from supply.model import Lane, Network, Store, Warehouse
from supply.solve import solve_optimum

TOL = 1e-6


def check(name, cond):
    assert cond, f"FAILED: {name}"
    print(f"  ok  {name}")


def close(a, b):
    return abs(a - b) <= 1e-4


def test_model():
    net = regions()
    check("regions is balanced (60 = 60)", net.is_balanced())
    check("regions demand is mandatory", net.all_mandatory())
    check("bottleneck has surplus supply (80 > 50)",
          bottleneck().total_supply() == 80 and bottleneck().total_demand() == 50)
    sh = shortage()
    check("shortage is short of supply (30 < 40)",
          sh.total_supply() == 30 and sh.total_demand() == 40)
    check("shortage demand is elastic", not sh.all_mandatory())
    check("lane lookup works", net.lane("W1", "S3").cost == 5)
    check("unknown lane is None", net.lane("W2", "S1") is not None
          and net.lane("W1", "Sx") is None)


def _duality_holds(net, r):
    """Optimal cost = sum price*demand - sum rent*capacity (mandatory nets)."""
    lhs = r["cost"]
    rhs = (sum(r["prices"][s.id] * s.demand for s in net.stores)
           - sum(r["rents"][w.id] * w.capacity for w in net.warehouses))
    return close(lhs, rhs)


def test_regions():
    net = regions()
    r = solve_optimum(net)
    check("regions feasible", r["feasible"])
    check("regions optimal cost is 180", close(r["cost"], 180))
    check("regions serves all demand", all(close(v, 0) for v in r["unserved"].values()))
    check("regions prices: S1=S2=2, S3=5",
          close(r["prices"]["S1"], 2) and close(r["prices"]["S2"], 2)
          and close(r["prices"]["S3"], 5))
    check("regions has no binding capacity (rents 0)",
          all(close(v, 0) for v in r["rents"].values()))
    check("regions satisfies LP duality", _duality_holds(net, r))


def test_bottleneck():
    net = bottleneck()
    r = solve_optimum(net)
    check("bottleneck optimal cost is 200", close(r["cost"], 200))
    check("bottleneck price is the marginal 6 everywhere",
          close(r["prices"]["S1"], 6) and close(r["prices"]["S2"], 6))
    check("bottleneck: cheap DC earns rent 5", close(r["rents"]["W1"], 5))
    check("bottleneck: pricey DC earns no rent", close(r["rents"]["W2"], 0))
    check("bottleneck ships W1 to capacity (20)",
          close(sum(u for k, u in r["flow"].items() if k.startswith("W1->")), 20))
    check("bottleneck satisfies LP duality", _duality_holds(net, r))


def test_shortage():
    net = shortage()
    r = solve_optimum(net)
    check("shortage optimal cost is 90", close(r["cost"], 90))
    check("shortage optimal welfare is 140", close(r["welfare"], 140))
    check("shortage serves Flagship fully", close(r["served"]["S1"], 20))
    check("shortage leaves 10 of the Outlet unserved", close(r["unserved"]["S2"], 10))
    check("shortage lost value is 30", close(r["lostValue"], 30))
    check("shortage prices: Flagship 6, Outlet 3",
          close(r["prices"]["S1"], 6) and close(r["prices"]["S2"], 3))
    check("shortage: scarce DC earns rent 2", close(r["rents"]["W1"], 2))


def test_market_matches_optimum():
    """The auction reaches the LP optimum on every scenario."""
    for build in (regions, bottleneck, shortage):
        net = build()
        opt, mkt = solve_optimum(net), solve_market(net)
        check(f"{net.name}: market cost equals optimum",
              close(opt["cost"], mkt["cost"]))
        check(f"{net.name}: market served equals optimum",
              all(close(opt["served"][s], mkt["served"][s]) for s in opt["served"]))
        if "welfare" in opt:
            check(f"{net.name}: market welfare equals optimum",
                  close(opt["welfare"], mkt["welfare"]))


def test_market_discovers_prices():
    """Converged object prices are the LP capacity rents (up to eps)."""
    for build in (regions, bottleneck, shortage):
        net = build()
        opt, mkt = solve_optimum(net), solve_market(net)
        ok = all(abs(mkt["warehousePrice"][w] - opt["rents"][w]) <= 0.1
                 for w in opt["rents"])
        check(f"{net.name}: market prices match capacity rents", ok)


def test_market_frames():
    mkt = solve_market(bottleneck())
    check("frames are downsampled to the cap", len(mkt["frames"]) <= 120)
    check("more rounds were actually run than frames kept",
          mkt["rounds"] > len(mkt["frames"]))
    last = mkt["frames"][-1]
    check("final frame agrees with the result cost", close(last["cost"], mkt["cost"]))
    check("final frame leaves no one still bidding", last["bidding"] == 0)


def test_market_deterministic():
    a, b = solve_market(shortage()), solve_market(shortage())
    check("auction is deterministic (same cost)", close(a["cost"], b["cost"]))
    check("auction is deterministic (same rounds)", a["rounds"] == b["rounds"])
    check("market is feasible where mandatory demand is met",
          solve_market(regions())["feasible"])


def test_evaluate():
    """evaluate() scores the optimum's own flow back to the same numbers."""
    net = shortage()
    opt = solve_optimum(net)
    ev = evaluate(net, opt["flow"])
    check("evaluate reproduces optimum cost", close(ev["cost"], opt["cost"]))
    check("evaluate reproduces optimum welfare", close(ev["welfare"], opt["welfare"]))
    check("evaluate reports % served", close(ev["pctServed"], 75.0))


def test_greedy_ties_on_easy():
    """Greedy matches the optimum when the instance is forgiving."""
    for build in (regions, bottleneck):
        net = build()
        check(f"{net.name}: greedy ties the optimum cost",
              close(solve_greedy(net)["cost"], solve_optimum(net)["cost"]))


def test_greedy_gap_welfare():
    """Shortage: myopia burns scarce supply on low-value demand."""
    net = shortage()
    g = solve_greedy(net)
    check("greedy shortage welfare is 100 (vs optimum 140)", close(g["welfare"], 100))
    check("greedy shortage cost is 60", close(g["cost"], 60))


def test_greedy_gap_cost():
    """Myopia: the cheapest single lane strands the store with no backup."""
    net = myopia()
    check("myopia optimum cost is 50", close(solve_optimum(net)["cost"], 50))
    check("myopia greedy cost is 100 (twice the optimum)",
          close(solve_greedy(net)["cost"], 100))


def test_compare():
    """The head-to-head: market is always optimal; greedy can fall behind."""
    for build in (regions, bottleneck, shortage, myopia):
        net = build()
        c = compare(net)
        check(f"{net.name}: compare reports three methods",
              set(c["comparison"]) == {"optimum", "market", "greedy"})
        check(f"{net.name}: market efficiency is 1.0",
              close(c["comparison"]["market"]["efficiency"], 1.0))
        check(f"{net.name}: optimum efficiency is 1.0",
              close(c["comparison"]["optimum"]["efficiency"], 1.0))
    eff = compare(myopia())["comparison"]["greedy"]["efficiency"]
    check("myopia: greedy efficiency is 0.5", close(eff, 0.5))
    eff_s = compare(shortage())["comparison"]["greedy"]["efficiency"]
    check("shortage: greedy efficiency is ~0.714", close(eff_s, 0.7143))


def _raises(fn, exc):
    try:
        fn()
    except exc:
        return True
    return False


def test_model_validation():
    """Node ids can't clash across kinds or contain the flow-key separator."""
    check("warehouse/store id clash rejected", _raises(
        lambda: Network("x", [Warehouse("A", "W", 5, 0, 0)],
                        [Store("A", "S", 5, 1, 1)], []), AssertionError))
    check("id containing '->' rejected", _raises(
        lambda: Network("x", [Warehouse("W->1", "W", 5, 0, 0)],
                        [Store("S", "S", 5, 1, 1)], []), AssertionError))


def test_market_integer_guard():
    """Fractional units must raise, not silently solve a different instance."""
    frac = Network("frac", [Warehouse("W", "W", 10.5, 0, 0)],
                   [Store("S", "S", 7, 1, 1)], [Lane("W", "S", 1)])
    check("fractional capacity raises", _raises(lambda: solve_market(frac),
                                                ValueError))
    frac2 = Network("frac2", [Warehouse("W", "W", 10, 0, 0)],
                    [Store("S", "S", 7.5, 1, 1)], [Lane("W", "S", 1)])
    check("fractional demand raises", _raises(lambda: solve_market(frac2),
                                              ValueError))


def test_market_edge_guards():
    """Zero-lane networks and tiny frame caps don't crash."""
    lonely = Network("nolanes", [Warehouse("W", "W", 5, 0, 0)],
                     [Store("S", "S", 5, 1, 1, value=3)], [])
    r = solve_market(lonely)
    check("zero-lane elastic market runs", r["served"]["S"] == 0)
    check("downsample to 1 keeps the last frame",
          _downsample([{"i": 1}, {"i": 2}, {"i": 3}], 1) == [{"i": 3}])


def test_compare_stranded_demand():
    """A method that strands mandatory demand scores 0, not >1."""
    # Greedy grabs W1->S1 (cheapest) and strands S2, whose only route is W1.
    net = Network("strand",
                  [Warehouse("W1", "W1", 10, 0.2, 0.3),
                   Warehouse("W2", "W2", 10, 0.8, 0.3)],
                  [Store("S1", "S1", 10, 0.3, 0.7),
                   Store("S2", "S2", 10, 0.7, 0.7)],
                  [Lane("W1", "S1", 1), Lane("W1", "S2", 2), Lane("W2", "S1", 3)])
    c = compare(net)
    g = c["comparison"]["greedy"]
    check("stranding greedy is marked infeasible", g["feasible"] is False)
    check("stranding greedy efficiency is 0", g["efficiency"] == 0.0)
    check("market still solves the stranding net",
          c["comparison"]["market"]["efficiency"] == 1.0)


def test_stranded_scenario():
    """The shipped 'stranded' scenario: greedy fails half the network."""
    check("stranded is a shipped scenario",
          any(s["id"] == "stranded" for s in SCENARIOS))
    net = stranded()
    c = compare(net)
    check("stranded optimum cost is 50",
          close(c["comparison"]["optimum"]["cost"], 50))
    g = c["comparison"]["greedy"]
    check("stranded greedy serves only 50%", close(g["pctServed"], 50))
    check("stranded greedy is infeasible", g["feasible"] is False)
    check("stranded greedy efficiency is 0", g["efficiency"] == 0.0)
    check("stranded market is optimal",
          close(c["comparison"]["market"]["efficiency"], 1.0))


def test_compare_nonpositive_welfare():
    """Ratio direction is undefined when optimal welfare <= 0; don't invert."""
    net = Network("mixed",
                  [Warehouse("W1", "W1", 20, 0.2, 0.5, cost=5)],
                  [Store("S1", "S1", 10, 0.5, 0.5),           # mandatory, dear
                   Store("S2", "S2", 5, 0.8, 0.5, value=2)],  # elastic, cheap
                  [Lane("W1", "S1", 5), Lane("W1", "S2", 1)])
    c = compare(net)
    for m, row in c["comparison"].items():
        check(f"{m}: non-positive-welfare eff is 1.0 or None",
              row["efficiency"] in (1.0, None))


if __name__ == "__main__":
    for fn in [test_model, test_regions, test_bottleneck, test_shortage,
               test_market_matches_optimum, test_market_discovers_prices,
               test_market_frames, test_market_deterministic,
               test_evaluate, test_greedy_ties_on_easy, test_greedy_gap_welfare,
               test_greedy_gap_cost, test_compare,
               test_model_validation, test_market_integer_guard,
               test_market_edge_guards, test_compare_stranded_demand,
               test_stranded_scenario, test_compare_nonpositive_welfare]:
        print(fn.__name__)
        fn()
    print("\nAll supply engine smoke tests passed.")
