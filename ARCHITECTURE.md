# loan-calc — calculator architecture (calculator.py)

This document explains the purpose and behavior of each function in `loan-calc/loan_calc/calculator.py`.  
No code changes are made—this is strictly documentation.

---

## Module-level constants & imports

- `import math`
  - Used for `ceil()` and `log()` when solving for remaining tenure.

- `from datetime import date`
  - Used by `summary()` to compute a projected last EMI month (based on an optional start date).

- `DEFAULT_CURRENCY = "INR"`
  - Currency label included in `summary()` output.

---

## `_monthly_rate(annual_rate)`

**Signature:** `_monthly_rate(annual_rate)`  
**Returns:** monthly interest rate `r` as a float.

**Behavior:**
- Converts an annual percentage rate to a monthly decimal rate:
  - `r = annual_rate / 1200`
- Rounds to **4 decimal places**:
  - `r = round(annual_rate / 1200, 4)`

**Role in the system:**
- All EMI-related calculations rely on this helper to translate annual rate (percent) into a per-month decimal rate.

---

## `emi(principal, annual_rate, tenure_months)`

**Signature:** `emi(principal, annual_rate, tenure_months)`  
**Returns:** EMI amount (monthly payment), rounded to 2 decimals.

**Behavior:**
1. Validates inputs:
   - `tenure_months` must be positive, else raises `ValueError("tenure must be positive")`
   - `principal` must be positive, else raises `ValueError("principal must be positive")`
2. Computes monthly rate `r` using `_monthly_rate(annual_rate)`.
3. Special case when `r == 0`:
   - Returns `principal / tenure_months` rounded to 2 decimals.
4. Otherwise uses the standard amortizing loan EMI formula:
   - Let `f = (1 + r) ** tenure_months`
   - EMI = `principal * r * f / (f - 1)`
5. Rounds the result to 2 decimals.

**Role in the system:**
- Central primitive for computing:
  - total paid amounts
  - interest totals
  - amortisation schedules
  - offer comparisons
  - prepayment calculations

---

## `total_payment(principal, annual_rate, tenure_months)`

**Signature:** `total_payment(principal, annual_rate, tenure_months)`  
**Returns:** Total of all monthly payments over the tenure.

**Behavior:**
- Computes EMI via `emi(...)`.
- Multiplies by `tenure_months`.
- Rounds to 2 decimals.

**Meaning:**
- Represents **sum of all instalments** (principal+interest).

---

## `total_interest(principal, annual_rate, tenure_months)`

**Signature:** `total_interest(principal, annual_rate, tenure_months)`  
**Returns:** Total interest paid over the tenure.

**Behavior:**
- Uses `total_payment(...) - principal`
- Rounds to 2 decimals.

**Meaning:**
- Interest component aggregated over the entire amortization period.

---

## `amortisation_schedule(principal, annual_rate, tenure_months)`

**Signature:** `amortisation_schedule(principal, annual_rate, tenure_months)`  
**Returns:** List of row dicts describing each month’s EMI breakdown.

**Structure of each row:**
- `"month"`: 1-based month index
- `"emi"`: the EMI amount used for that month (rounded)
- `"interest"`: interest portion for the month (rounded)
- `"principal"`: principal portion for the month (rounded)
- `"balance"`: remaining balance after the month, floored at 0.0

**Behavior:**
1. Computes monthly rate `r = _monthly_rate(annual_rate)`.
2. Computes fixed EMI: `instalment = emi(principal, annual_rate, tenure_months)`.
3. Initializes:
   - `balance = principal`
   - `rows = []`
4. Iterates `for month in range(1, tenure_months):`
   - This loop runs **tenure_months - 1** times.
5. For each `month`:
   - `interest = round(balance * r, 2)`
   - `principal_part = round(instalment - interest, 2)`
6. There is a conditional special handling:
   - `if month == tenure_months:`
     - Intended as a final-month adjustment, but given the loop condition it may never trigger (because `month` never reaches `tenure_months` in `range(1, tenure_months)`).
   - In the `else` branch:
     - `instalment_amt = instalment`
7. Updates remaining:
   - `balance = round(balance - principal_part, 2)`
   - Stores `balance` as `max(balance, 0.0)` in the row.
8. Returns `rows`.

**Role in the system:**
- Used by:
  - `outstanding_after()` to retrieve balance after a number of months
  - `prepayment_savings()` to locate the balance at the prepayment month and sum interest already paid

---

## `outstanding_after(principal, annual_rate, tenure_months, months_paid)`

**Signature:** `outstanding_after(principal, annual_rate, tenure_months, months_paid)`  
**Returns:** Remaining loan balance after `months_paid` months (rounded / float).

**Behavior:**
1. If `months_paid <= 0`, returns `principal` rounded to 2 decimals.
2. Builds a schedule: `sched = amortisation_schedule(...)`.
3. If `months_paid > len(sched)`, returns `0.0`.
4. Otherwise returns:
   - `sched[months_paid - 1]["balance"]`

**Meaning:**
- “Outstanding principal” after a partial repayment period.

---

## `remaining_tenure(balance, annual_rate, instalment)`

**Signature:** `remaining_tenure(balance, annual_rate, instalment)`  
**Returns:** Number of months required to repay `balance` when paying `instalment` each month, rounded up.

**Behavior:**
1. Computes monthly rate from an annual percent:
   - `r = annual_rate / 100`
   - (Note: compared to `_monthly_rate`, this is a different conversion approach.)
2. If `balance <= 0`:
   - returns `0`
3. If `r == 0`:
   - returns `math.ceil(balance / instalment)`
4. Validates payment sufficiency:
   - If `instalment <= balance * r`, raises:
     - `ValueError("instalment too small to repay the loan")`
5. Solves for number of payments using logarithms:
   - `n = -log(1 - balance * r / instalment) / log(1 + r)`
6. Returns `math.ceil(n)`

**Meaning:**
- Computes how many months remain after a lump-sum reduction, assuming the same fixed instalment continues.

---

## `prepayment_savings(principal, annual_rate, tenure_months, prepay_month, prepay_amount)`

**Signature:** `prepayment_savings(principal, annual_rate, tenure_months, prepay_month, prepay_amount)`  
**Returns:** Dict of EMI / tenure / interest savings metrics.

**Docstring (as written):**
- `"Keep the same EMI after a lump-sum prepayment and shorten the tenure."`

**Behavior outline:**
1. Compute original fixed EMI:  
   - `instalment = emi(principal, annual_rate, tenure_months)`
2. Compute original amortisation schedule:
   - `sched = amortisation_schedule(...)`
3. Determine outstanding balance just before/at prepayment month:
   - `balance = sched[prepay_month - 1]["balance"]`
4. Apply lump-sum prepayment:
   - `new_balance = balance - prepay_amount`
   - if `new_balance <= 0`: `months_left = 0`
   - else:
     - `months_left = remaining_tenure(new_balance, annual_rate, instalment)`
5. Compute original time remaining:
   - `original_left = tenure_months - prepay_month`
6. Compute interest already paid before prepayment:
   - `interest_paid_so_far = sum(row["interest"] for row in sched[:prepay_month])`
7. Compute overall original totals:
   - `original_interest = total_interest(principal, annual_rate, tenure_months)`
8. Model new payoff totals (conceptual):
   - `new_total = instalment * prepay_month + prepay_amount + instalment * months_left`
   - `new_interest = new_total - principal`
9. Return metrics (with rounding):
   - `"emi"`: the original EMI
   - `"months_saved"`: `original_left - months_left`
   - `"new_tenure"`: `prepay_month + months_left`
   - `"interest_saved"`: rounded `original_interest - new_interest` to 2 decimals
   - `"interest_paid_before_prepayment"`: rounded `interest_paid_so_far` to 2 decimals

**Role in the system:**
- Integrates multiple primitives:
  - amortisation schedule positioning
  - remaining tenure computation
  - interest totals
- Used to quantify the benefit of lump-sum prepayment.

---

## `compare_offers(principal, offers)`

**Signature:** `compare_offers(principal, offers)`  
**Returns:** List of offer summaries sorted by lowest total cost.

**Expected `offers` item shape:**
Each `o` in `offers` is expected to contain:
- `"bank"`: bank name/identifier
- `"rate"`: annual interest rate (percent)
- `"tenure"`: tenure in months
Optional:
- `"processing_fee_pct"`: fee as percent of principal (defaults to 0)

**Behavior:**
1. Initialize `out = []`.
2. For each offer `o`:
   - `e = emi(principal, o["rate"], o["tenure"])`
   - `ti = total_interest(principal, o["rate"], o["tenure"])`
   - `fee = o.get("processing_fee_pct", 0) * principal / 100`
3. Append dict:
   - `"bank"`, `"emi"`, `"total_interest"`
   - `"processing_fee"` rounded to 2 decimals
   - `"total_cost"` rounded `ti + fee` to 2 decimals
4. Sort results by `"total_cost"` ascending:
   - `out.sort(key=lambda x: x["total_cost"])`
5. Return `out`.

**Meaning:**
- Produces a comparable metric including interest + processing fee.

---

## `eligible_amount(monthly_income, existing_emis, annual_rate, tenure_months, foir=0.5)`

**Signature:**  
`eligible_amount(monthly_income, existing_emis, annual_rate, tenure_months, foir=0.5)`  
**Returns:** Maximum loan principal eligible under FOIR constraints, rounded to 2 decimals.

**Behavior:**
1. Compute available monthly EMI capacity:
   - `available = monthly_income * foir - existing_emis`
2. If `available <= 0`:
   - return `0.0`
3. Compute monthly rate `r = _monthly_rate(annual_rate)`.
4. Special case `r == 0`:
   - return `available * tenure_months` rounded to 2 decimals.
5. Otherwise derives principal from EMI formula algebra:
   - `f = (1 + r) ** tenure_months`
   - Eligible principal:
     - `available * (f - 1) / (r * f)`
   - rounded to 2 decimals.

**Meaning:**
- Converts allowable EMI payment into an equivalent loan principal.

---

## `format_inr(amount)`

**Signature:** `format_inr(amount)`  
**Returns:** Indian-currency string with rupee symbol and comma grouping, e.g. `₹1,23,456.78`.

**Behavior:**
1. Track negativity:
   - `neg = amount < 0`
2. Normalize absolute value and round to 2 decimals:
   - `amount = abs(round(amount, 2))`
3. Convert to string with 2 decimals:
   - `whole, frac = f"{amount:.2f}".split(".")`
4. Apply Indian numbering format:
   - if `len(whole) > 3`:
     - keep last 3 digits in `tail`
     - group remaining digits in 2-digit chunks (`..,xx,yy` pattern)
5. Return:
   - negative sign if needed
   - `₹` + formatted whole + `.` + frac

**Meaning:**
- Pure formatting helper for UI / summaries.

---

## `schedule_to_csv(rows, path)`

**Signature:** `schedule_to_csv(rows, path)`  
**Behavior:**
- Opens `path` for writing text.
- Writes header:
  - `month,emi,interest,principal,balance`
- For each `r` in `rows`, writes a CSV line:
  - `month, emi, interest, principal, balance`

**Note:**
- It directly uses row dict keys matching those produced by `amortisation_schedule()`.

---

## `summary(principal, annual_rate, tenure_months, start=None)`

**Signature:**  
`summary(principal, annual_rate, tenure_months, start=None)`  
**Returns:** Dict suitable for display/reporting.

**Behavior:**
1. If `start` is not provided:
   - sets `start = date.today()`
2. Computes EMI `e = emi(principal, annual_rate, tenure_months)`.
3. Computes projected end date (year/month):
   - `end_year = start.year + (start.month - 1 + tenure_months) // 12`
   - `end_month = (start.month - 1 + tenure_months) % 12 + 1`
4. Returns dict fields:
   - `"principal"` formatted via `format_inr(principal)`
   - `"rate"` as string like `"{annual_rate}% p.a."`
   - `"tenure"` like `"{tenure_months} months"`
   - `"emi"` formatted via `format_inr(e)`
   - `"total_interest"` formatted via `format_inr(total_interest(...))`
   - `"total_payment"` formatted via `format_inr(total_payment(...))`
   - `"last_emi"` formatted as `"{end_year}-{end_month:02d}"`
   - `"currency"` set to `DEFAULT_CURRENCY` (INR)

**Meaning:**
- Provides human-readable loan metrics.

---

## Function interdependencies (high-level)

- `_monthly_rate()` is used by:
  - `emi()`, `eligible_amount()`, `amortisation_schedule()`
- `emi()` is used by:
  - `total_payment()`, `total_interest()`
  - `amortisation_schedule()`
  - `prepayment_savings()`
  - `compare_offers()`
  - `summary()`
- `amortisation_schedule()` is used by:
  - `outstanding_after()`
  - `prepayment_savings()`
- `remaining_tenure()` is used by:
  - `prepayment_savings()`
- `total_interest()` is used by:
  - `prepayment_savings()`
  - `compare_offers()`
  - `summary()`

---
