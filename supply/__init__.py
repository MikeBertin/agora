"""Agora supply engine — logistics allocation as a transportation problem.

The same scarce supply, allocated three ways and compared on cost and welfare:
a central LP optimum, an auction-algorithm market, and a greedy baseline.
"""
from .model import Warehouse, Store, Lane, Network, Flow
from .instances import SCENARIOS, BY_ID
from .solve import solve_optimum
from .market import solve_market
from .greedy import solve_greedy
from .analysis import evaluate, compare

__all__ = ["Warehouse", "Store", "Lane", "Network", "Flow",
           "SCENARIOS", "BY_ID", "solve_optimum", "solve_market",
           "solve_greedy", "evaluate", "compare"]
