# loan-calc (starter for Assignment P1)

A small Python module for retail loan calculations: EMI, amortisation schedule, prepayment savings, offer comparison and eligibility.

It has no tests and no documentation. Users report that some numbers are wrong. Your job is described in Assignment P1.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Try it

```bash
python cli.py 1000000 9 240
python cli.py 1000000 9 240 --schedule
python cli.py 1000000 9 240 --prepay-month 24 --prepay-amount 200000
```

## Run tests (once you have written them)

```bash
pytest --cov=loan_calc --cov-report=term-missing
```

Put your tests in the `tests/` folder.

# Acceptance Verification

## Results Summary

- **Pytest:** `17 passed`
  - Command: `python -m pytest --cov=loan_calc --cov-report=term-missing --cov-fail-under=85`
- **Coverage:** **90.27%** (threshold **85%** reached)
- **EMI reference value (real package):**
  - `emi(1_000_000, 9.0, 240) = 8997.26`

## Acceptance Criteria

- [x] All three seeded bugs found and fixed  
  - Evidence: test suite passes (`17 passed`) with coverage enforced.
  - Fixed bugs (as diagnosed and corrected during this project work):
    1. `amortisation_schedule()` omitted the final month because its range excluded `tenure_months`; (schedule length / final balance issue)
    2. `remaining_tenure()` incorrectly used the annual rate as if it were a monthly rate; (rate conversion / tenure computation issue)
    3. `prepayment_savings()` used an excessive requested prepayment instead of capping it at outstanding balance; (excessive prepayment handling / negative savings issue)

- [x] Test suite passes with coverage >= 85%  
  - Command: `python -m pytest --cov=loan_calc --cov-report=term-missing --cov-fail-under=85`  
  - Result: **17 passed**, Coverage **90.27%**

- [x] EMI for ₹10,00,000 at 9% p.a. over 240 months matches ₹8,997 (+/- ₹1)  
  - Calculated value: `emi(1_000_000, 9.0, 240) = 8997.26`  
  - Range check: inclusive **₹8,996 to ₹8,998** → **PASS**

- [x] ARCHITECTURE.md is accurate and project-specific  
  - Evidence: `ARCHITECTURE.md` was reviewed against the current codebase implementation before being relied upon.

- [x] PROMPT_LOG.md records an AI correction  
  - Recorded correction (in `loan-calc/PROMPT_LOG.md`):
    - Initial exact remaining-tenure expectation was too strict because `emi()` rounds to two decimals and `remaining_tenure()` uses `math.ceil()`, so the tenure may be the original tenure or one additional month.
    - The test expectation was revised to allow `tenure_months <= months <= tenure_months + 1`.
