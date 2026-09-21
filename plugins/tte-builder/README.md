# tte-builder

A Cowork plugin that helps researchers specify a target trial and its emulation
for pharmacoepidemiology and comparative-effectiveness studies.

## What it does

The plugin contains a single skill, `tte-builder`, that walks the user through the
target-trial protocol table in four phases:

1. **Ideal target trial** — the protocol is specified component by component
   (eligibility, time zero, strategies, assignment, outcome, follow-up, contrast,
   analysis), with the user accepting, disputing, or modifying each entry.
2. **Emulation with the data** — each component is mapped to the available cohort,
   every feasibility compromise is flagged, and time zero is aligned on the data.
3. **Threat assessment** — for each component, the bias it can admit (immortal
   time, prevalent-user bias, positivity failure, the ITT / per-protocol gap) is
   assessed and ranked.
4. **Implications** — the adjustment set (handed off to the **dag-builder** skill),
   the causal contrast, the estimator, and sensitivity analyses.

The load-bearing decision is **time zero**: eligibility, strategy assignment, and
the start of follow-up must be aligned at one instant, definable from information
available then. The skill refuses to advance past Phase 1 until time zero passes
its check.

Every design choice is documented with a plain-language justification, a
confidence tag, and PubMed-verified references searched at runtime. The skill
never fabricates citations from memory.

## When the skill triggers

Typical phrasings: "specify a target trial for…", "emulate a trial of…", "build
the TTE protocol table", "what should my time zero be", "is this immortal time",
"new-user active-comparator design", "ITT versus per-protocol for my study",
"sequence of trials".

If the user instead asks "what should I control for" or to draw the causal graph,
that is the **dag-builder** skill.

## Outputs

- A protocol table in Quarto / `kbl` form (two or three columns)
- A baseline-by-strategy balance table (R)
- An immortal-time person-time diagnostic (R)
- An emulation-dataset skeleton (R)
- A structured protocol JSON, exportable
- A footnote block in the book's citation format

## What's bundled

- `skills/tte-builder/SKILL.md` — the operational guide Claude follows
- `skills/tte-builder/design_patterns/` — seven YAML reference files: the
  assignability gate, the eight protocol components, time zero, study designs
  (new-user / active-comparator), causal contrasts (ITT / per-protocol), the
  benchmarking evidence, and the biases prevented
- `skills/tte-builder/examples/tte_statins_chd_phase1.md` — a worked Phase 1
  example (statins → coronary heart disease)

## Companion skills

- **dag-builder** — construct the baseline DAG and read off the adjustment set
  (Phase 4). The two skills are designed to be used together: `tte-builder` owns
  the protocol, `dag-builder` owns the graph.
- **ipw** — implement inverse-probability weighting / marginal structural models
  for the per-protocol contrast under time-varying confounding.
- **adat** — log the AI's contribution to each design decision as a publishable
  audit trail.

## A note on scope

There is no `dagitty` equivalent doing mechanical work behind the protocol table:
specifying a target trial is structured reasoning, not computation. The skill's
value is the gated order (especially the time-zero gate), the reference
attachment, the threat assessment, and the table / diagnostic code it generates.

## Author

Ülo Maiväli

## Version

0.1.0 (initial release)
