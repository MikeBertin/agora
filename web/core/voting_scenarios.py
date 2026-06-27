"""Curated voting scenarios, each illustrating one lesson in social choice."""
from __future__ import annotations

A, B, C, D = "A", "B", "C", "D"

SCENARIOS = [
    {
        "id": "clear",
        "label": "A clear winner",
        "blurb": "When opinion is lopsided, every rule agrees — and the winner is "
                 "also the Condorcet winner. The interesting cases are the others.",
        "candidates": [A, B, C],
        "profile": [(6, (A, B, C)), (2, (B, C, A)), (1, (C, B, A))],
    },
    {
        "id": "spoiler",
        "label": "The spoiler effect",
        "blurb": "C can't win, but by splitting the vote it hands plurality to A — "
                 "even though a majority prefers B to A. Drop C and B wins. IRV, "
                 "Borda and Condorcet all see through it; plurality doesn't.",
        "candidates": [A, B, C],
        "profile": [(10, (A, B, C)), (6, (B, A, C)), (5, (C, B, A))],
    },
    {
        "id": "cycle",
        "label": "The Condorcet paradox",
        "blurb": "35% rank A>B>C, 33% B>C>A, 32% C>A>B. Majorities prefer A to B, "
                 "B to C — and C to A. The head-to-head graph is a cycle, so there "
                 "is no Condorcet winner at all. Collective preference is irrational.",
        "candidates": [A, B, C],
        "profile": [(35, (A, B, C)), (33, (B, C, A)), (32, (C, A, B))],
    },
    {
        "id": "alldiffer",
        "label": "All four rules disagree",
        "blurb": "The same 17 ballots elect four different winners: plurality picks A, "
                 "Borda picks C, instant-runoff picks D, and the Condorcet winner is B. "
                 "There is no single 'right' answer — only a choice of rule.",
        "candidates": [A, B, C, D],
        "profile": [(5, (A, B, C, D)), (4, (B, C, D, A)),
                    (5, (D, C, B, A)), (3, (A, C, D, B))],
    },
]

# Live mode explores the three cyclic blocs whose balance creates/destroys a cycle.
LIVE_RANKINGS = [(A, B, C), (B, C, A), (C, A, B)]
LIVE_CANDIDATES = [A, B, C]
