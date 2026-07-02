"""Curated matching markets, each illustrating one lesson in two-sided matching.

Every market is small enough to check by hand — and small enough that the
tests *enumerate* all stable matchings and *brute-force* all misreports, so
the lessons (proposer-optimality, one-sided strategy-proofness, the rural
hospital theorem) are proved on the instance, not just quoted.
"""
from __future__ import annotations

SCENARIOS = [
    {
        "id": "clear",
        "label": "A clear match",
        "blurb": "Everyone agrees on how the other side ranks — the market is "
                 "assortative. There is exactly one stable matching, so it "
                 "makes no difference who proposes: watch the same rejection "
                 "cascade sort everyone into place from either side. The "
                 "interesting cases are the others.",
        "a": {"label": "Candidates", "prefs": {
            "Ana":  ["Koru", "Lumen", "Onyx"],
            "Ben":  ["Koru", "Lumen", "Onyx"],
            "Cleo": ["Koru", "Lumen", "Onyx"],
        }},
        "b": {"label": "Companies", "prefs": {
            "Koru":  ["Ana", "Ben", "Cleo"],
            "Lumen": ["Ana", "Ben", "Cleo"],
            "Onyx":  ["Ana", "Ben", "Cleo"],
        }},
    },
    {
        "id": "chain",
        "label": "The domino effect",
        "blurb": "Five candidates, four jobs. Ana loses Koru to Eve, so she "
                 "takes Lumen from Ben; Ben takes Onyx from Cleo; Cleo takes "
                 "Pico from Dex — and Dex, bumped last, ends with nothing. "
                 "Engagements are only ever tentative: one rejection can "
                 "reshuffle everyone downstream, which is exactly why the "
                 "algorithm defers acceptance until the market goes quiet.",
        "a": {"label": "Candidates", "prefs": {
            "Ana":  ["Koru", "Lumen"],
            "Ben":  ["Lumen", "Onyx"],
            "Cleo": ["Onyx", "Pico"],
            "Dex":  ["Pico", "Koru"],
            "Eve":  ["Koru", "Lumen"],
        }},
        "b": {"label": "Companies", "prefs": {
            "Koru":  ["Eve", "Ana", "Dex"],
            "Lumen": ["Ana", "Ben", "Eve"],
            "Onyx":  ["Ben", "Cleo"],
            "Pico":  ["Cleo", "Dex"],
        }},
    },
    {
        "id": "direction",
        "label": "Who proposes, wins",
        "blurb": "A perfectly crossed market: this instance has three stable "
                 "matchings. When candidates propose, every candidate lands "
                 "their first choice and every company its last; flip the "
                 "direction and it inverts exactly. Deferred acceptance "
                 "always delivers the best stable outcome for the proposing "
                 "side — the algorithm's one big thumb on the scale.",
        "a": {"label": "Candidates", "prefs": {
            "Ana":  ["Koru", "Lumen", "Onyx"],
            "Ben":  ["Lumen", "Onyx", "Koru"],
            "Cleo": ["Onyx", "Koru", "Lumen"],
        }},
        "b": {"label": "Companies", "prefs": {
            "Koru":  ["Ben", "Cleo", "Ana"],
            "Lumen": ["Cleo", "Ana", "Ben"],
            "Onyx":  ["Ana", "Ben", "Cleo"],
        }},
    },
    {
        "id": "strategy",
        "label": "The profitable lie",
        "blurb": "With candidates proposing, no candidate can ever gain by "
                 "misreporting — we brute-force every list they could submit. "
                 "But Koru can: by striking Ana off its list entirely, the "
                 "rejection ricochets around the market and delivers Koru its "
                 "first choice, Ben. Strategy-proofness only ever holds for "
                 "the proposing side.",
        "strategy": True,
        "a": {"label": "Candidates", "prefs": {
            "Ana": ["Koru", "Lumen"],
            "Ben": ["Lumen", "Koru"],
        }},
        "b": {"label": "Companies", "prefs": {
            "Koru":  ["Ben", "Ana"],
            "Lumen": ["Ana", "Ben"],
        }},
    },
    {
        "id": "hospitals",
        "label": "Hospitals & residents",
        "blurb": "Many-to-one: hospitals take several residents (City and "
                 "Rural have two posts each). Rhea and Sam trade Metro and "
                 "Bay depending on who proposes — but in every stable "
                 "matching Rural fills only one of its two posts, with Wren, "
                 "and Vik is left unmatched. Which posts stay vacant and who "
                 "goes unplaced are facts of the market, not of the "
                 "algorithm: the rural hospital theorem.",
        "a": {"label": "Residents", "prefs": {
            "Rhea": ["Metro", "Bay"],
            "Sam":  ["Bay", "Metro"],
            "Tao":  ["City", "Rural"],
            "Uma":  ["City"],
            "Vik":  ["City"],
            "Wren": ["Rural", "City"],
        }},
        "b": {"label": "Hospitals", "prefs": {
            "City":  ["Tao", "Uma", "Vik", "Wren"],
            "Metro": ["Sam", "Rhea"],
            "Bay":   ["Rhea", "Sam"],
            "Rural": ["Wren", "Tao"],
        }, "caps": {"City": 2, "Metro": 1, "Bay": 1, "Rural": 2}},
    },
]

BY_ID = {s["id"]: s for s in SCENARIOS}
