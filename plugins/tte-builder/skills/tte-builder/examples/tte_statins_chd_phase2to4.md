# Worked Phases 2–4 — Statins and primary prevention of coronary heart disease

Continues `tte_statins_chd_phase1.md`. The case follows the statin emulation in
UK electronic medical records reported by Danaei et al. The estimates quoted in
Phase 4 are the published results of that study (see reference and DOI below).

---

## Phase 2 — Emulate with the cohort

### 2.1 Dataset

Primary-care electronic medical records: one record per patient per follow-up
month, with LDL and other covariates updated over time, statin prescriptions
dated, and incident CHD events captured. Treatment is recorded as a prescription,
not as ingestion.

### 2.2 Per-component emulation and compromise flags

| Component | Emulation | Compromise | Future info? |
|-----------|-----------|------------|--------------|
| Eligibility | Statin-naïve, no prior CHD, eligible for primary prevention at the month assessed | Statin-naïve proxied by no prescription in the lookback window | no |
| Time zero | The first month the patient meets eligibility | none | no |
| Strategies | "Initiate and continue" vs "do not initiate", per month | Adherence proxied by prescription fills, not ingestion (**poor-proxy**) | no |
| Assignment | Initiator vs non-initiator at time zero | No randomisation; assume baseline exchangeability | no |
| Outcome | Incident CHD from time zero | none | no |
| Follow-up | Person-months from time zero to event/censoring | none | no |

### 2.3 Single versus sequential time zero

Eligibility recurs every month a patient remains statin-naïve and CHD-free.
**Sequential design**: each eligible month opens a new trial in which the patient
is an initiator or a non-initiator; trials are pooled, with the variance
accounting for a patient appearing in several. This is the design Danaei et al.
used.

### 2.4 Baseline-by-strategy balance

At time zero, initiators differ from non-initiators on the determinants of
prescribing (lipids, comorbidity, age) — confounding by indication, made visible
at baseline. This imbalance is the quantity the adjustment set must remove; it is
a stated assumption attached to the assignment row, not a hidden defect.

### 2.5 Immortal-time diagnostic

Because follow-up starts at time zero and assignment uses only the time-zero
prescription status, there is no pre-assignment person-time. A naïve alternative —
classifying a patient as a "statin user" for ever filling a statin and counting
months before the first fill as treated — would credit the user group with
event-free waiting time and bias the estimate. The aligned design forbids this by
construction (Output Template C demonstrates the magnitude on a person-period
table).

---

## Phase 3 — Threat assessment

| Rank | Component | Threat | Present? | Direction | Severity |
|------|-----------|--------|----------|-----------|----------|
| 1 | Assignment | Residual confounding by indication | residual | toward harm if under-adjusted | moderate |
| 2 | Strategies | Adherence proxied by fills (exposure misclassification) | residual | toward null (per-protocol) | small–moderate |
| 3 | Follow-up | Immortal time | controlled (by alignment) | — | negligible |
| 4 | Eligibility | Prevalent-user bias | controlled (new-user design) | — | negligible |
| 5 | Assignment | Positivity (some covariate strata all-treated/all-untreated) | check on adjustment set | unknown | small |

Caveats: severities are categorical judgements; the direction of residual
confounding depends on how completely baseline lipids and comorbidity are
measured; positivity is checked against the adjustment set (Phase 4), not asserted.

---

## Phase 4 — Implications

### 4.1 Adjustment set — hand off to dag-builder

Read the baseline confounders off a baseline DAG (invoke **dag-builder**):
age, sex, baseline LDL and other lipids, blood pressure, diabetes, smoking,
comorbidity, and prior healthcare use. Check: all measured at or before time zero;
none a descendant of statin initiation; positivity plausible across strata.

### 4.2 Causal contrast

**Per-protocol** is the question (the effect of sustained statin use), confirmed
from Phase 1. The ITT analogue is reported alongside it as the assignment-only
effect.

### 4.3 Analytic method

Per-protocol estimation must adjust for the post-baseline variables that drive
adherence and are changed by earlier treatment (LDL falls under treatment) —
treatment-confounder feedback. Standard regression fails here. Use an IP-weighted
marginal structural model or the g-formula → **connect to the ipw skill**. Bayesian
g-computation gives the posterior of the counterfactual contrast.

### 4.4 Results (published estimates, for illustration)

According to PubMed, the Danaei et al. emulation reported, for CHD:

- ITT analogue (initiators vs non-initiators): HR 0.89 (0.73–1.09)
- Per-protocol (2 years of use vs no use): HR 0.84 (0.54–1.30)
- As-treated: HR 0.79 (0.41–1.41)
- Conventional current-users vs never-users: HR **1.31 (1.04–1.66)**

The conventional current-vs-never comparison shows spurious *harm* — the signature
of confounding by indication and prevalent-user bias — while the new-user,
sequential-trial emulation recovers a *protective* effect consistent with the
randomised-trial evidence. This is the payoff of the protocol: the design choices
made in Phases 1–2 are what separate the two answers.

### 4.5 Sensitivity and corroboration

- Compare the single-time-zero design as a robustness check on the sequential one.
- Negative-control outcomes to detect residual confounding.
- The emulation is benchmarkable against statin primary-prevention RCTs; broad
  concordance of well-specified emulations with RCTs supports the approach
  (`design_patterns/05_benchmarking.yaml`).

---

## Reference

According to PubMed: Danaei G, García Rodríguez LA, Cantero OF, Logan R, Hernán MA,
"Observational data for comparative effectiveness research: an emulation of
randomised trials of statins and primary prevention of coronary heart disease,"
*Stat Methods Med Res* 2013;22:70-96
([DOI](https://doi.org/10.1177/0962280211403603); PMID 22016461). Verified via the
PubMed connector on 2026-06-30.
