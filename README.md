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
| **[Negotiation](web/negotiation/)** | Bilateral bargaining | A candidate and an employer haggle over a five-issue job offer under a deadline. Watch the bidding dance against the exact Pareto frontier, the concession curves, and a frequency model learning the opponent's hidden priorities. **Built.** |
| **Auctions** | Mechanism design | English / Dutch / Vickrey / double auctions; price discovery and revenue equivalence. *Planned.* |
| **Voting** | Social choice | Plurality, Borda, instant-runoff and the Condorcet cycle. *Planned.* |
| **Distributed optimisation** | DCOP | Independent agents coordinating under constraints — the backbone of resource allocation and scheduling. *Planned.* |

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
experiments/run.py    # generates the JSON traces + mirrors core/ into web/
web/                  # static site (GitHub Pages)
  index.html          #   landing
  negotiation/        #   the demo (Canvas viz + Pyodide live mode)
  data/               #   precomputed traces + manifest
  core/               #   copy of the engine, fetched by Pyodide
tests/test_core.py    # engine smoke tests
```

The Python core is deliberately dependency-free and small enough that the whole
outcome space is enumerable, so the Pareto frontier and Nash point are computed
**exactly**, not approximated. The `auctions` and `dcop` modules planned next
are intended to be lifted into a resource-allocation / supply-optimisation
engine — multi-agent mechanism design is the foundation that work builds on.

## Running it

The site is static — open `web/index.html`, or serve the folder:

```sh
cd web && python3 -m http.server 8761
```

Regenerate the precomputed traces (and refresh the in-browser engine copy):

```sh
python3 experiments/run.py
```

Run the engine tests:

```sh
python3 tests/test_core.py
```

## Notes

Rebuilt from the COMP6203 GENIUS coursework (Java). Named for the
[agora](https://en.wikipedia.org/wiki/Agora) — market, assembly, and meeting
place of the Greek city.
