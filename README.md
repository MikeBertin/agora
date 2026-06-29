# Agora

**Multi-agent systems, in the browser.**

The Athenian *agora* was at once a marketplace, a bargaining floor and a voting
assembly. This project revisits the core problems of my **Intelligent Agents**
MSc module (COMP6203) — automated **negotiation**, **auctions**, **voting** and
distributed **optimisation** — as interactive, self-contained web demos backed
by a small, reusable Python engine.

🔗 **[Live site](https://mikebertin.github.io/agora/)**

Unlike a pure-JavaScript toy, the negotiation logic lives in a real Python
package (`core/`). The same code runs two ways:

- **offline**, to precompute negotiation traces the site plays back instantly, and
- **live in your browser**, via [Pyodide](https://pyodide.org) — the demo runs
  the actual Python engine in WebAssembly so you can change parameters and
  re-run with no server.

## The demos

| | | |
|---|---|---|
| **[Negotiation](docs/negotiation/)** | Bilateral bargaining | A candidate and an employer haggle over a five-issue job offer under a deadline. Watch the bidding dance against the exact Pareto frontier, the concession curves, and a frequency model learning the opponent's hidden priorities. **Built.** |
| **[Auctions](docs/auctions/)** | Mechanism design | English / Vickrey / first-price / Dutch auctions under independent private values; bid shading, the revenue-equivalence theorem converging live, and the same-mean/different-variance revenue distribution. **Built.** |
| **[Voting](docs/voting/)** | Social choice | Plurality, Borda, instant-runoff and Condorcet over curated profiles (spoiler, the Condorcet paradox, and a profile where all four rules disagree), with a live majority graph. **Built.** |
| **[Distributed optimisation](docs/dcop/)** | DCOP | Graph colouring as decentralised resource allocation: autonomous agents resolve conflicts with only local information via DSA and MGM. **Built.** |
| **[Supply allocation](docs/supply/)** | Logistics / network flow | The transportation problem solved three ways — a central LP optimum, an auction-algorithm market where demand bids for capacity, and a greedy baseline — compared on cost, welfare and the efficiency gap. The market reaches the optimum *and* rediscovers its dual prices by bidding. **Built.** |

## The negotiation agents

The two flagship agents come straight from the GENIUS coursework:

- **Frequency v1 (faithful)** — a direct port of the submitted `group2.MyAgent`:
  a fixed 0.8 utility target and acceptance only at the very deadline.
- **Frequency v2 (improved)** — adds time-dependent (Boulware) concession and
  AC-next acceptance.

Both share the same **frequency opponent model** — estimating the opponent's
issue weights from how concentrated their offers are, and value utilities from
offer frequency rank — and the same **Pareto-seeking bid choice**: among bids
good enough for us, offer the one the model thinks is best for the opponent.

Pitting them against four opponents (Boulware, Conceder, Hardliner, Random)
tells an honest story rather than a tidy one: v1 can *stonewall a pure
conceder* for a high payoff, but is brittle — it reaches **no deal** against a
hardliner and **loses the head-to-head to v2**, which concedes gracefully and
agrees faster.

## Architecture

```
core/                 # reusable pure-Python engine (no dependencies)
  domain.py           #   discrete multi-issue domains + additive utility
  model.py            #   frequency opponent model (the MyAgent port)
  agents.py           #   v1, v2, Boulware, Conceder, Hardliner, Random
  protocol.py         #   SAOP alternating-offers session runner -> trace
  analysis.py         #   exact Pareto frontier + Nash point (enumerated)
  domains.py          #   the Job Offer domain + candidate/employer profiles
  auctions.py         #   English/Vickrey/first-price/Dutch + revenue equivalence
  voting.py           #   plurality / Borda / IRV / Condorcet + pairwise margins
  voting_scenarios.py #   curated profiles (spoiler, paradox, all-differ)
  dcop.py             #   graph colouring via DSA and MGM
supply/               # logistics allocation engine (needs scipy; not in browser)
  model.py            #   transportation network: warehouses, stores, lanes
  instances.py        #   four hand-checkable logistics scenarios
  solve.py            #   central LP optimum + dual shadow prices (scipy/HiGHS)
  market.py           #   auction algorithm -> allocation + clearing prices
  greedy.py           #   myopic cheapest-lane baseline
  analysis.py         #   score any flow + three-way efficiency comparison
experiments/          # one runner per demo; each writes docs/data/*.json
  run.py  run_auctions.py  run_voting.py  run_dcop.py   # + mirror core/ into docs/
  run_supply.py       # writes docs/data/supply.json (playback-only; needs venv)
docs/                  # static site (served by GitHub Pages from /docs)
  index.html          #   landing
  negotiation/ auctions/ voting/ dcop/   # the demos (Canvas viz + Pyodide live)
  supply/             #   supply demo (Canvas viz, precomputed playback)
  data/               #   precomputed traces + manifests
  core/               #   copy of the engine, fetched by Pyodide
tests/test_core.py    # engine smoke tests (37 checks)
tests/test_supply.py  # supply engine smoke tests (needs venv; 66 checks)
```

The `core/` engine is deliberately dependency-free and small enough that exact
results are computed, not approximated (the negotiation outcome space and the
auction equilibria are enumerated/closed-form). The `supply/` package is where
the `auctions` (mechanism design) and `dcop` (decentralised allocation) threads
are carried forward into a real resource-allocation engine: it solves the
logistics transportation problem as a central LP, as a decentralised auction
market, and greedily — then measures the efficiency gap between them. It is the
one engine that needs a third-party solver (scipy), so unlike the other four it
runs offline only, not live in the browser.

## Running it

The site is static — open `docs/index.html`, or serve the folder:

```sh
cd docs && python3 -m http.server 8761
```

Regenerate the precomputed traces (and refresh the in-browser engine copy in `docs/core`):

```sh
for r in run run_auctions run_voting run_dcop; do python3 experiments/$r.py; done
```

The supply engine is the exception — it needs scipy, so set up a venv first:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python experiments/run_supply.py      # writes docs/data/supply.json
```

Run the engine tests (supply needs the venv):

```sh
python3 tests/test_core.py
.venv/bin/python tests/test_supply.py
```

## Notes

Rebuilt from the COMP6203 GENIUS coursework (Java). Named for the
[agora](https://en.wikipedia.org/wiki/Agora) — market, assembly, and meeting
place of the Greek city.
