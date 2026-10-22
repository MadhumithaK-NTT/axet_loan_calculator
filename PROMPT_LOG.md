# Prompt Log

## Purpose
This file records how AI assistance was used during this project. It also records what was independently verified (via local code inspection and running the test suite). When AI guidance was incomplete or incorrect, this log records the correction that was actually applied based on observed repo behavior.

## Entry 1 — Documentation and architecture
AI was used to help draft clean documentation/type-oriented explanations for the project’s calculation functions. The resulting documentation was reviewed against the actual codebase structure and function behavior before being used.

## Entry 2 — Test design
AI helped propose pytest coverage across core behaviors including:
- reference EMI calculation;
- zero-interest behavior;
- one-month loan amortisation/schedule shape;
- large-principal EMI sanity (positive and finite);
- excessive prepayment handling and expected non-negative savings;
- amortisation schedules, INR formatting, CSV output;
- offer comparison sorting/keys;
- eligibility computation constraints; and
- summary output structure and last-EMI formatting.

Test expectations were reviewed to ensure they described intended business behavior rather than current buggy behavior (i.e., aligning assertions with the corrected implementation).

## Entry 3 — AI suggestion that was corrected
Initial AI-proposed test expectation:
`remaining_tenure(principal, annual_rate, emi(principal, annual_rate, tenure_months)) == tenure_months`

Why this was too strict:
- `emi()` rounds to two decimals;
- `remaining_tenure()` uses `math.ceil()` when estimating months.
A small rounding difference can make the computed repayment duration slightly greater than the original tenure. In that case, `math.ceil()` can yield one additional month beyond the original tenure.

Corrected expectation:
- Instead of requiring exact equality, the test should allow the computed months to be within the original tenure through at most one additional month (i.e., `tenure_months <= months <= tenure_months + 1`).

Lesson:
Financial calculations and tests must account for documented rounding (two-decimal EMI) and rounding-up behavior (`ceil`), rather than assuming strict equality of tenure.

(Verification against repo: the final remaining-tenure test asserts `tenure_months <= months <= tenure_months + 1`.)

## Entry 4 — Bug diagnosis and verification
AI-assisted review helped identify and verify three separate bugs:
1. `amortisation_schedule()` omitted the final month (schedule length / final balance issue).
2. `remaining_tenure()` used the interest rate in the wrong interpretation (producing inconsistent tenure).
3. `prepayment_savings()` did not cap excessive prepayment at the outstanding balance (leading to invalid negative interest savings).

Each diagnosis was checked using pytest failures and then confirmed by rerunning the relevant tests after applying minimal fixes. Changes were reviewed before they were applied, and no claim is made that AI independently authored the final code.
