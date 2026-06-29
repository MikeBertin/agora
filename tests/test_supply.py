"""Smoke tests for the Agora supply engine.

Needs scipy, so run under the project venv:
  .venv/bin/python tests/test_supply.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supply import BY_ID
from supply.instances import bottleneck, regions, shortage
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


if __name__ == "__main__":
    for fn in [test_model, test_regions, test_bottleneck, test_shortage]:
        print(fn.__name__)
        fn()
    print("\nAll supply engine smoke tests passed.")
