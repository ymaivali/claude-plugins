---
name: tte-builder
description: Specifies and reviews a target trial and its emulation for pharmacoepidemiology and comparative-effectiveness studies. Use when the user asks to "specify a target trial", "emulate a trial", "build a TTE protocol table", "what is my time zero", "is this immortal time", "new-user active-comparator design", "ITT versus per-protocol", or describes an observational drug study and asks how to design it as a trial emulation. Walks through four phases: specify the ideal target trial component by component; emulate each with the available cohort, flagging compromises; assess each component's threats (immortal time, prevalent-user bias, positivity, the ITT / per-protocol gap); and derive the adjustment set and estimator. The adjustment-set step hands off to the dag-builder skill. Design choices carry PubMed-verified references (never fabricated) and confidence tags. Outputs a protocol table (Quarto/kbl), a balance table, an immortal-time diagnostic, and a protocol JSON.
---

# Target Trial Emulation Builder — Operational Guide

## What This Skill Does

Guides a researcher through specifying a target trial and its emulation with
observational data, for pharmacoepidemiology and comparative-effectiveness
studies. Works in four phases:

1. **Ideal target trial** — the protocol is specified component by component,
   with the user accepting, disputing, or modifying each entry. The left column
   of the protocol table: what a randomised trial would do.
2. **Emulation with the data** — each component is mapped to the available
   cohort, every feasibility compromise is flagged, and time zero is aligned.
   The right column of the protocol table: how the cohort enacts each component.
3. **Threat assessment** — for each component, the bias it can admit (immortal
   time, prevalent-user bias, positivity failure, the ITT / per-protocol gap) is
   assessed and the threats are ranked.
4. **Implications** — the adjustment set (handed off to the **dag-builder**
   skill), the causal contrast, the estimator, and the sensitivity analyses.

Every design choice is documented with a plain-language justification, a
confidence tag, and PubMed-verified references searched at runtime. The skill
never fabricates citations from memory; if PubMed returns nothing relevant and no
anchoring reference applies, it says so and gives the search terms.

The single load-bearing decision is **time zero**. Once eligibility, strategy
assignment, and the start of follow-up are aligned at one instant — and that
instant is definable from information available then — the misalignment biases
are closed off. Every other component is downstream of it. The skill refuses to
advance past Phase 1 until time zero passes its check.

---

## Trigger Conditions

Invoke this skill when a researcher:
- Asks to specify, build, review, or critique a target trial or its emulation
- Asks to build a TTE protocol table or "the emulation table"
- Asks what their time zero / index date should be, or whether a proposed start
  introduces immortal time
- Describes an observational drug study and asks how to design it as a trial
  emulation
- Asks about new-user, active-comparator, or sequential-trial designs
- Asks whether to estimate an intention-to-treat or a per-protocol effect

If the user instead asks "what should I control for", "is this a collider", or
to draw the causal graph, that is the **dag-builder** skill — invoke it instead,
or hand off to it at Phase 4.

---

## Session State

Track these variables throughout the conversation. Update after each user
response. Never advance to the next component until the user has responded to the
current proposal.

```
STATE:
  phase: 1 | 2 | 3 | 4
  research_question:
    exposure_strategy: ~      # a RULE that could be assigned, not an observed variable
    outcome: ~
    population: ~
    estimand: itt_analogue | per_protocol | undecided
    assignable: ~             # GATE: can the exposure in principle be assigned? true/false
  protocol:                   # one entry per component (see component schema)
    eligibility: ~
    time_zero: ~
    strategies: ~
    assignment: ~
    outcome: ~
    follow_up: ~
    contrast: ~
    analysis: ~
  emulation:
    dataset_described: false
    compromises: []           # Phase 2: each row's feasibility compromise + proxy quality
    time_zero_design: single | sequential | undecided
  threats: []                 # Phase 3: per-component bias entries, ranked
  adjustment_set: ~           # Phase 4: handed to / returned from dag-builder
  analytic_implication: standardisation_or_ipw | msm_or_gformula | bayesian_gcomp
```

### Component Schema

```yaml
component:
  name: string                # eligibility | time_zero | strategies | ...
  ideal: string               # what the target trial would do (left column)
  emulation: string           # how the cohort enacts it (right column)
  compromise: string | null   # feasibility substitution, if any (Phase 2)
  uses_future_info: boolean    # TRUE is a defect — must be resolved before advancing
  threat: string | null       # the bias this component can admit (Phase 3)
  confidence: established | well-supported | plausible | contested | assumed | uncertain
  references: []              # list of reference objects (see reference schema)
  check: string               # the verification gate that must pass
  status: proposed | accepted | disputed | modified
```

### Reference Schema

```yaml
reference:
  citation: string
  type: textbook | journal | report
  doi: string | null
  verified: boolean           # true only if confirmed via PubMed MCP or known DOI/textbook
```

---

## Phase 1: Specify the Ideal Target Trial

### 1.1 Research Question Intake

Before specifying any component, collect the following as a single structured
block — do not proceed until all fields are answered.

```
To specify your target trial, I need the question stated precisely.
Please answer the following:

1. EXPOSURE STRATEGY: What is the intervention, stated as a RULE that could be
   assigned? (e.g., "initiate statin and continue", not "statin use"). Static
   ("always / never") or dynamic ("treat when LDL exceeds a threshold")?

2. OUTCOME: The primary outcome, defined precisely (incident MI, all-cause
   mortality, hospitalisation for X, a lab threshold crossing).

3. POPULATION: Who is eligible? (diagnosis, age range, care setting, database).

4. ESTIMAND: The effect of being ASSIGNED a strategy (intention-to-treat
   analogue) or the effect of ADHERING to it (per-protocol)? If unsure, say so —
   this is resolved in Phase 4, but flag it now.
```

### 1.2 The Gate — Is the Exposure Assignable?

Before any component, run the assignability gate:

> Does the exposure name an intervention that could, in principle, be assigned?

- **Yes** (a drug, a dose, a screening interval, a treat-when-indicated rule):
  proceed.
- **No** (a body-mass index, a socioeconomic position, a race as a state rather
  than an intervention on it): **stop**. There is no trial to emulate, even
  hypothetically; consistency fails and the estimand is not well defined. Offer
  the two responses: (a) reformulate the question until it names an intervention
  ("the effect of a specified weight-loss programme" rather than "the effect of
  obesity"), or (b) treat the question as one for triangulation across designs,
  not trial emulation. Cite the limits-of-the-framing references
  (`design_patterns/00_assignability.yaml`).

### 1.3 Component Specification Order

Specify the eight components in this order. The order is not cosmetic: each
component's check must pass before the next, and time zero (step 4) is the hinge
the rest depend on.

```
1. Question & estimand     → gate: exposure is assignable (1.2)
2. Eligibility             → check: every criterion decidable at/before time zero
3. Treatment strategies    → check: each is a concrete, assignable rule (consistency)
4. TIME ZERO  ★            → check: eligibility + assignment + follow-up start
                                    coincide; instant definable from info available then
5. Outcome & follow-up     → check: follow-up begins AT time zero, not before
6. Causal contrast         → check: ITT analogue vs per-protocol stated; PP ⇒ time-varying plan
7. Adjustment set          → check: baseline-only; no descendant of treatment; positivity (→ dag-builder)
8. Analysis plan           → check: matches the contrast and the adjustment set
```

### 1.4 Component Proposal Format

Propose one component at a time, in the order above. For each:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPONENT: [name]   (component k of 8)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IDEAL TRIAL:      [what a randomised trial would do]
EMULATION:        [how the cohort would enact it — filled fully in Phase 2]
CONFIDENCE:       [design-choice confidence + reference if applicable]
CHECK:            [the gate that must pass]
⚠ USES FUTURE INFO?  [yes/no — yes is a defect; resolve before advancing]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Accept, dispute, or modify this component?
```

Draw component templates and their references from `design_patterns/`. For design
choices (new-user, active-comparator, single vs sequential time zero, static vs
dynamic strategies), present the canonical option, its rationale, and the
trade-off, then let the user choose.

### 1.5 Time-Zero Alignment Check (the load-bearing gate)

At component 4, run this explicitly and do not advance until it passes:

1. Name the instant that defines time zero.
2. Confirm eligibility is assessed at that instant (not before, not after).
3. Confirm strategy assignment is made at that instant.
4. Confirm follow-up begins at that instant.
5. Confirm the instant is definable using only information available at or before
   it. Ask, for each variable used to define it: "Is this knowable at time zero?"
6. If a patient is eligible at several visits, decide: a single time zero per
   patient, or a **sequence of trials** with one time zero per eligible visit,
   pooled (`design_patterns/02_time_zero.yaml`).

If any of 2–5 fails, the design admits immortal-time or prevalent-user bias.
State which, and revise before proceeding.

### 1.6 Reference Protocol

Two-track, identical in spirit to the dag-builder skill:

**Track 1 — PubMed search** (for design choices and bias claims): search PubMed,
extract first author, journal, year, DOI; mark `verified: true` only on a
confirmed result. If nothing relevant, say so and give the search terms. Never
fabricate.

**Track 2 — anchoring references** (stable, mark `verified: true`):
- Hernán MA, Robins JM, "Using Big Data to Emulate a Target Trial When a
  Randomized Trial Is Not Available," *Am J Epidemiol* 2016;183:758-764
  (DOI 10.1093/aje/kwv254).
- Hernán MA, Wang W, Leaf DE, "Target Trial Emulation: A Framework for Causal
  Inference From Observational Data," *JAMA* 2022;328:2446-2447
  (DOI 10.1001/jama.2022.21383).
- Hernán MA, Robins JM, *What If*, Chapman & Hall/CRC, 2020 (Part III).

**Honesty rule**: if neither track yields a usable reference, say so, give the
structural argument, and provide the search terms.

### 1.7 Phase 1 Completion

When the user is satisfied with all eight components, produce:
1. The **protocol table** (Output Template A — Quarto/kbl, two or three columns).
2. A **summary of the load-bearing decisions** (time zero; single vs sequential;
   new-user / active-comparator; ITT vs per-protocol).

Then ask:
> "Phase 1 is complete. Shall we proceed to Phase 2 (emulating each component
> with your dataset and aligning time zero on the data), or revise the protocol
> first?"

---

## Phase 2: Emulate with the Cohort

### 2.1 Dataset Description

Collect: the unit and time structure (person-level or person-period rows), the
variables available and when each is measured relative to time zero, how
treatment is recorded (prescription fill, dispensing, administration), and the
follow-up structure.

### 2.2 Per-Component Emulation and Compromise Flags

For each protocol component, fill the EMULATION column and record any compromise:

```
COMPONENT: [name]
EMULATION: [how the cohort enacts it]
COMPROMISE: [the substitution forced by the data] | none
  PROXY QUALITY: direct | good-proxy | acceptable | poor-proxy | unavailable
⚠ USES FUTURE INFO? [re-check on the actual variables]
```

Common compromises to probe: time zero proxied by a date that is only partly
pre-baseline; adherence proxied by fills rather than ingestion; eligibility
criteria that silently use post-baseline codes.

### 2.3 Single versus Sequential Time Zero

If the data support eligibility at several visits, present both designs and the
trade-off (data efficiency vs. analytic complexity), and record the choice in
STATE (`design_patterns/02_time_zero.yaml`).

### 2.4 Baseline-by-Strategy Balance Table

Build the time-zero baseline by assigned strategy (Output Template B) and inspect
covariate balance. State plainly: any imbalance is confounding by indication made
visible at time zero — a stated assumption attached to the assignment row, to be
removed by the adjustment set, not a hidden defect.

### 2.5 Immortal-Time Diagnostic

If the cohort is in person-period form, run the immortal-time diagnostic (Output
Template C): classify person-time by the strategy assigned at time zero versus by
ever-treatment, and report the share of person-time that is pre-initiation
waiting time and the events it contains (zero, by construction). Use this to show
whether a proposed misaligned definition would manufacture bias.

---

## Phase 3: Threat Assessment

### 3.1 Scope

For each protocol component, assess the bias it can admit given the emulation
choices. This is a qualitative supplement, ranked by concern.

### 3.2 Threat Entry Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPONENT: [name]
THREAT: immortal-time | prevalent-user | misaligned-start selection |
        positivity failure | ITT/PP conflation | residual confounding
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MECHANISM: [how this component, as emulated, would admit the bias]
PRESENT?:  controlled | residual | present
DIRECTION: toward null | away from null | unknown
SEVERITY:  negligible | small | moderate | large | severe
FIX / SENSITIVITY: [design fix if available; else sensitivity analysis]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 3.3 Threat Ranking Summary

```
THREAT RANKING (highest concern → lowest):
Rank | Component | Threat | Present? | Direction | Severity
-----|-----------|--------|----------|-----------|---------
  1  | ...       | ...    | ...      | ...       | ...
```

### 3.4 Caveats

State explicitly: these are categorical judgements, not calibrated numbers; the
direction of confounding bias may be uncertain; positivity is checked against the
adjustment set, not asserted; the per-protocol contrast carries time-varying
confounding that Phase 4 must address.

---

## Phase 4: Implications and Next Steps

### 4.1 Adjustment Set — Hand Off to dag-builder

The adjustment set is a graphical question. Do not derive it ad hoc here. Hand
off to the **dag-builder** skill:

> "The adjustment set should be read off a baseline DAG. I can invoke the
> dag-builder skill to construct it: the confounders that block the back-door
> paths from assignment to outcome, with no descendant of treatment in the set."

Carry the result back into STATE `adjustment_set`. Check: baseline-only variables;
no descendant of the exposure; positivity plausible across its strata.

### 4.2 Resolve the Causal Contrast

- **ITT analogue**: compares strategies as assigned at time zero; robust to
  post-baseline behaviour but estimates the effect of an assignment nobody
  followed past time zero. Estimated by comparing initiators vs non-initiators,
  standardised or weighted on baseline covariates.
- **Per-protocol**: compares sustained adherence; usually the question for a drug
  taken over time, but requires adjusting for the post-baseline variables that
  drive adherence — treatment-confounder feedback.

### 4.3 Analytic Method Recommendation

- **`standardisation_or_ipw`** (one-shot treatment, baseline confounders only):
  standardisation or inverse-probability weighting on baseline covariates.
- **`msm_or_gformula`** (sustained strategy, time-varying confounding with
  feedback): a marginal structural model (IP weighting) or the g-formula.
  **Connect to the ipw skill** for implementation.
- **`bayesian_gcomp`**: Bayesian g-computation when posterior uncertainty over
  the counterfactual contrast is wanted.

### 4.4 Sensitivity and Corroboration

- Sequential-trials design as a robustness check against the single-time-zero
  choice.
- Negative-control outcomes / exposures to detect residual confounding.
- Where the effect is benchmarkable, compare to the corresponding randomised
  trial (the reconciliation literature, `design_patterns/05_benchmarking.yaml`).

---

## Output Templates

### Template A — Protocol Table (Quarto / kbl, book house style)

```r
tibble(
  Component = c("Eligibility", "Time zero (start of follow-up)", "Treatment strategies",
                "Assignment", "Outcome", "Follow-up", "Causal contrast", "Analysis plan"),
  `Target trial` = c(
    "[ideal eligibility]", "[the instant of randomisation]", "[static/dynamic strategies]",
    "[randomise at time zero]", "[incident outcome]", "[from time zero to event/end]",
    "[ITT and/or per-protocol]", "[ITT: compare groups; PP: adjust for adherence]"),
  `Emulation with the cohort` = c(
    "[eligible new users at time zero]", "[the defining instant; pre-baseline info only]",
    "[per-visit rules]", "[no randomisation; assume conditional exchangeability]",
    "[the recorded outcome]", "[person-period rows from time zero]",
    "[initiators vs non-initiators; sustained-strategy contrast]",
    "[standardise/weight; MSM or g-formula; Bayesian g-computation]")
) |>
  kbl(caption = "The target trial and its emulation.") |>
  kable_styling(full_width = FALSE) |>
  column_spec(1, bold = TRUE) |>
  column_spec(2:3, width = "16em")
```

### Template B — Baseline-by-Strategy Balance Table

```r
trial <- obs |>
  filter(k == 1, A_lag == 0) |>                 # eligible new users; time zero = first visit
  transmute(id,
            assignment = if_else(A == 1, "initiate", "withhold"),
            sbp0 = sbp_lag, severity, age, diabetes)

trial |>
  group_by(assignment) |>
  summarise(n = n(),
            `mean SBP at t0` = mean(sbp0),
            `mean severity`  = mean(severity),
            `mean age`       = mean(age),
            `prop. diabetic` = mean(diabetes), .groups = "drop") |>
  kbl(digits = 1, caption = "Baseline of the emulated trial, by assigned strategy at time zero.") |>
  kable_styling(full_width = FALSE)
```

### Template C — Immortal-Time Person-Time Diagnostic

```r
person <- obs |>
  group_by(id) |>
  summarise(ever = max(A),
            first_treat = if (any(A == 1)) min(k[A == 1]) else Inf, .groups = "drop")
obs2 <- obs |> left_join(person, by = "id")

rate_tv   <- obs2 |> group_by(current = A) |> summarise(rate = mean(Y), .groups = "drop")
rr_tv     <- with(rate_tv, rate[current == 1] / rate[current == 0])     # time-respecting
rate_ever <- obs2 |> group_by(group = ever) |> summarise(rate = mean(Y), .groups = "drop")
rr_ever   <- with(rate_ever, rate[group == 1] / rate[group == 0])       # immortal-time error

immortal       <- obs2 |> filter(ever == 1, k < first_treat)
share_immortal <- nrow(immortal) / sum(obs2$ever == 1)

c(time_aligned_RR = round(rr_tv, 3), immortal_RR = round(rr_ever, 3),
  immortal_share = round(share_immortal, 3), events_in_immortal_time = sum(immortal$Y))
```

### Template D — Emulation Dataset Skeleton (the protocol made mechanical)

```r
trial <- obs |>
  filter(k == 1, A_lag == 0) |>                 # steps 2 & 4: eligible new users; time zero = first visit
  transmute(id,
            assign = A,                          # step 4: assignment uses only the time-zero value
            sbp0 = sbp_lag, severity, age, diabetes)  # step 7: baseline confounders only
# step 5: follow-up and outcome read from k >= 1 only, never from before time zero
# step 9: confirm no column of `trial` was derived from a visit after k = 1
```

### Template E — Protocol JSON (structured, exportable)

```json
{
  "question": {"exposure_strategy": "", "outcome": "", "population": "", "estimand": ""},
  "protocol": {
    "eligibility": {"ideal": "", "emulation": "", "uses_future_info": false, "check": ""},
    "time_zero":   {"ideal": "", "emulation": "", "design": "single|sequential", "uses_future_info": false},
    "strategies":  {"ideal": "", "emulation": "", "type": "static|dynamic"},
    "assignment":  {"ideal": "", "emulation": ""},
    "outcome":     {"ideal": "", "emulation": ""},
    "follow_up":   {"ideal": "", "emulation": ""},
    "contrast":    {"type": "itt_analogue|per_protocol"},
    "analysis":    {"method": "standardisation_or_ipw|msm_or_gformula|bayesian_gcomp"}
  },
  "threats": [],
  "adjustment_set": [],
  "references": []
}
```

### Template F — Footnote Block (book CLAUDE.md format)

When generating prose for the book, collect references as inline footnotes,
definitions at the end of the chapter file:

```
[^ref-tte-bigdata]: Hernán MA, Robins JM, "Using Big Data to Emulate a Target Trial When a Randomized Trial Is Not Available," *Am J Epidemiol* 2016;183:758-764 ([DOI](https://doi.org/10.1093/aje/kwv254)).
```

---

## Companion Skills

- **dag-builder** — construct the baseline DAG and read off the adjustment set
  (Phase 4.1). The two skills are designed to be used together: tte-builder owns
  the protocol; dag-builder owns the graph.
- **ipw** — implement inverse-probability weighting / marginal structural models
  for the per-protocol contrast under time-varying confounding (Phase 4.3).
- **adat** — log the AI's contribution to each design decision as a publishable
  audit trail.

## A Note on What This Skill Does Not Do

There is no `dagitty` equivalent doing mechanical work behind the protocol table:
specifying a target trial is structured reasoning, not computation. The skill's
value is the gated order (especially the time-zero gate humans skip), the
reference attachment, the threat assessment, and the table / diagnostic code it
generates. The only genuine computation is the immortal-time diagnostic, which
demonstrates a bias rather than estimating an effect.
