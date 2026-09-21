# Worked Phase 1 — Statins and primary prevention of coronary heart disease

A compact illustration of Phase 1 (specify the ideal target trial). The case
mirrors the statin emulation that reconciled observational data with the
randomised-trial evidence.

## Intake

- **Exposure strategy:** initiate a statin and continue (static), versus do not
  initiate. Dynamic alternative: initiate once LDL exceeds a guideline threshold.
- **Outcome:** incident coronary heart disease event.
- **Population:** adults eligible for primary prevention, no prior CHD, not
  currently on a statin.
- **Estimand:** flagged as per-protocol (the effect of sustained statin use); to
  be confirmed in Phase 4.

## Assignability gate

A statin is a drug that could be assigned at time zero. **Pass** — there is a
trial to emulate.

## Components (proposed, with checks)

| # | Component | Ideal | Check | Future info? |
|---|-----------|-------|-------|--------------|
| 2 | Eligibility | Primary-prevention adults, no prior CHD, statin-naïve | Decidable at/before time zero | no |
| 3 | Strategies | "Initiate and continue" vs "do not initiate" | Executable per visit (consistency) | — |
| 4 | **Time zero** | The instant eligibility is met, strategy assigned, follow-up begins | Three coincide; pre-baseline info only | no |
| 5 | Outcome & follow-up | Incident CHD from time zero to event/censoring | Follow-up begins AT time zero | no |
| 6 | Contrast | Per-protocol (sustained use) | Commits to time-varying-confounding plan | — |

## Load-bearing decisions recorded

- **Time zero:** first visit at which a statin-naïve eligible patient is seen.
  Defined using only information available then.
- **Single vs sequential:** eligibility recurs across visits → **sequence of
  trials**, pooled, as in the statin reconciliation (Danaei et al. 2013).
- **New-user / comparator:** new-user design (statin-naïve at time zero). A
  non-initiator comparator is used here; an active comparator would narrow
  confounding by indication further where one exists.
- **Contrast:** per-protocol → Phase 4 will require a marginal structural model or
  the g-formula for treatment-confounder feedback (changing lipid levels driven by
  earlier statin use).

## Reference anchoring

- Danaei G, García Rodríguez LA, Cantero OF, Logan R, Hernán MA, "Observational
  data for comparative effectiveness research: an emulation of randomised trials of
  statins and primary prevention of coronary heart disease," *Stat Methods Med Res*
  2013;22:70-96 (DOI 10.1177/0962280211403603; PMID 22016461).
  *verified via PubMed 2026-06-30.*

## Next

Proceed to Phase 2: describe the dataset, fill the emulation column, align time
zero on the data, build the baseline-by-strategy balance table, and run the
immortal-time diagnostic.
