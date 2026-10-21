import math
from datetime import date
from os import PathLike
from typing import Any

DEFAULT_CURRENCY = "INR"


def _monthly_rate(annual_rate):
    r = round(annual_rate / 1200, 4)
    return r


def emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Compute the fixed monthly EMI for an amortizing loan.

    Args:
        principal: Loan principal. Must be > 0.
        annual_rate: Annual interest rate as a percentage (e.g., 9.0 for 9%).
        tenure_months: Loan tenure in months. Must be > 0.

    Returns:
        The EMI amount rounded to 2 decimals.

    Raises:
        ValueError: If `tenure_months <= 0` or `principal <= 0`.
    """
    if tenure_months <= 0:
        raise ValueError("tenure must be positive")
    if principal <= 0:
        raise ValueError("principal must be positive")
    r = _monthly_rate(annual_rate)
    if r == 0:
        return round(principal / tenure_months, 2)
    f = (1 + r) ** tenure_months
    return round(principal * r * f / (f - 1), 2)


def total_payment(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Compute the total payment over the tenure.

    Note:
        This multiplies the already-rounded EMI produced by `emi(...)` by
        `tenure_months`, and then rounds the result to 2 decimals.

    Args:
        principal: Loan principal.
        annual_rate: Annual interest rate as a percentage.
        tenure_months: Tenure in months.

    Returns:
        Total payment rounded to 2 decimals.
    """
    return round(emi(principal, annual_rate, tenure_months) * tenure_months, 2)


def total_interest(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Compute the total interest paid over the tenure.

    Args:
        principal: Loan principal.
        annual_rate: Annual interest rate as a percentage.
        tenure_months: Tenure in months.

    Returns:
        The total interest, computed as `total_payment(...) - principal`,
        rounded to 2 decimals.
    """
    return round(total_payment(principal, annual_rate, tenure_months) - principal, 2)


def amortisation_schedule(
    principal: float, annual_rate: float, tenure_months: int
) -> list[dict[str, int | float]]:
    """Build an amortisation schedule.

    Args:
        principal: Loan principal.
        annual_rate: Annual interest rate as a percentage.
        tenure_months: Loan tenure in months.

    Returns:
        A list of schedule rows. Each row includes:
          - "month" (int): 1-based month index
          - "emi" (float): EMI amount used for that row
          - "interest" (float): interest portion for the month
          - "principal" (float): principal portion for the month
          - "balance" (float): remaining balance after the row (clamped to >= 0.0)
    """
    r = _monthly_rate(annual_rate)
    instalment = emi(principal, annual_rate, tenure_months)
    balance = principal
    rows = []
    for month in range(1, tenure_months + 1):
        interest = round(balance * r, 2)
        principal_part = round(instalment - interest, 2)
        if month == tenure_months:
            principal_part = round(balance, 2)
            instalment_amt = round(principal_part + interest, 2)
        else:
            instalment_amt = instalment
        balance = round(balance - principal_part, 2)
        rows.append({
            "month": month,
            "emi": instalment_amt,
            "interest": interest,
            "principal": principal_part,
            "balance": max(balance, 0.0),
        })
    return rows


def outstanding_after(
    principal: float, annual_rate: float, tenure_months: int, months_paid: int
) -> float:
    """Compute outstanding principal after a given number of months.

    Behavior:
        - If `months_paid <= 0`, returns `principal` rounded to 2 decimals.
        - If `months_paid` exceeds the generated schedule length, returns 0.0.

    Args:
        principal: Loan principal.
        annual_rate: Annual interest rate as a percentage.
        tenure_months: Loan tenure in months.
        months_paid: Number of months elapsed/paid.

    Returns:
        Remaining balance after `months_paid`, or 0.0 if `months_paid` exceeds
        the generated schedule length.
    """
    if months_paid <= 0:
        return round(principal, 2)
    sched = amortisation_schedule(principal, annual_rate, tenure_months)
    if months_paid > len(sched):
        return 0.0
    return sched[months_paid - 1]["balance"]


def remaining_tenure(balance: float, annual_rate: float, instalment: float) -> int:
    """Estimate remaining months to repay a balance with a fixed instalment.

    Args:
        balance: Outstanding balance.
        annual_rate: Annual interest rate as a percentage (as used by this implementation).
        instalment: Monthly payment amount.

    Returns:
        Remaining tenure in whole months (rounded up). If `balance <= 0`, returns 0.

    Raises:
        ValueError: If the instalment is insufficient to repay a positive
            balance at the calculated interest rate.
    """
    r = _monthly_rate(annual_rate)
    if balance <= 0:
        return 0
    if r == 0:
        return math.ceil(balance / instalment)
    if instalment <= balance * r:
        raise ValueError("instalment too small to repay the loan")
    n = -math.log(1 - balance * r / instalment) / math.log(1 + r)
    return math.ceil(n)


def prepayment_savings(
    principal: float,
    annual_rate: float,
    tenure_months: int,
    prepay_month: int,
    prepay_amount: float,
) -> dict[str, int | float]:
    """Estimate the impact of a lump-sum prepayment while keeping the EMI fixed.

    The function calculates a new estimated tenure after applying the
    prepayment to the schedule balance.

    Args:
        principal: Original loan principal.
        annual_rate: Annual interest rate as a percentage.
        tenure_months: Original loan tenure in months.
        prepay_month: One-based month index at which the prepayment is applied.
        prepay_amount: Lump-sum prepayment amount.

    Returns:
        A dictionary containing:
            - emi: Original monthly EMI.
            - months_saved: Estimated reduction in remaining months.
            - new_tenure: Estimated revised tenure in months.
            - interest_saved: Estimated interest saving.
            - interest_paid_before_prepayment: Interest accumulated before
              the prepayment point.

    Notes:
        This function does not validate prepayment month values or negative
        prepayment amounts. A prepayment exceeding the outstanding balance is
        capped at that balance.
    """
    instalment = emi(principal, annual_rate, tenure_months)
    sched = amortisation_schedule(principal, annual_rate, tenure_months)
    balance = sched[prepay_month - 1]["balance"]
    effective_prepay = min(prepay_amount, balance)
    new_balance = balance - effective_prepay
    if new_balance <= 0:
        months_left = 0
    else:
        months_left = remaining_tenure(new_balance, annual_rate, instalment)
    original_left = tenure_months - prepay_month
    interest_paid_so_far = sum(row["interest"] for row in sched[:prepay_month])
    original_interest = total_interest(principal, annual_rate, tenure_months)
    new_total = instalment * prepay_month + effective_prepay + instalment * months_left
    new_interest = new_total - principal
    return {
        "emi": instalment,
        "months_saved": original_left - months_left,
        "new_tenure": prepay_month + months_left,
        "interest_saved": round(original_interest - new_interest, 2),
        "interest_paid_before_prepayment": round(interest_paid_so_far, 2),
    }


def compare_offers(principal: float, offers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare loan offers by total cost (interest + processing fee).

    Args:
        principal: Principal used to evaluate each offer.
        offers: List of offer dicts. Each offer must contain:
            - "bank": Bank name/identifier
            - "rate": Annual interest rate as a percentage
            - "tenure": Tenure in months
          Processing fee is optional:
            - "processing_fee_pct": Processing fee percentage of principal (defaults to 0)

    Returns:
        List of offer summary dicts sorted by "total_cost" ascending. Each summary dict
        includes: bank, emi, total_interest, processing_fee, total_cost.
    """
    out = []
    for o in offers:
        e = emi(principal, o["rate"], o["tenure"])
        ti = total_interest(principal, o["rate"], o["tenure"])
        fee = o.get("processing_fee_pct", 0) * principal / 100
        out.append({
            "bank": o["bank"],
            "emi": e,
            "total_interest": ti,
            "processing_fee": round(fee, 2),
            "total_cost": round(ti + fee, 2),
        })
    out.sort(key=lambda x: x["total_cost"])
    return out


def eligible_amount(
    monthly_income: float,
    existing_emis: float,
    annual_rate: float,
    tenure_months: int,
    foir: float = 0.5,
) -> float:
    """Compute eligible loan principal based on FOIR constraints.

    Notes:
        This function does not validate its inputs.

    Args:
        monthly_income: Applicant monthly income.
        existing_emis: Existing monthly EMI obligations.
        annual_rate: Annual interest rate as a percentage.
        tenure_months: Loan tenure in months.
        foir: Fraction of income allowed for EMI (default 0.5).

    Returns:
        Eligible principal rounded to 2 decimals.
        Returns 0.0 if the computed EMI capacity is zero or negative.
    """
    available = monthly_income * foir - existing_emis
    if available <= 0:
        return 0.0
    r = _monthly_rate(annual_rate)
    if r == 0:
        return round(available * tenure_months, 2)
    f = (1 + r) ** tenure_months
    return round(available * (f - 1) / (r * f), 2)


def format_inr(amount: float) -> str:
    """Format a numeric amount as an INR string.

    Args:
        amount: Monetary amount.

    Returns:
        A string like '₹1,23,456.78'. Rounds to two decimals, uses Indian digit
        grouping, and preserves a negative sign if the input is negative.
    """
    neg = amount < 0
    amount = abs(round(amount, 2))
    whole, frac = f"{amount:.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts) + "," + tail
    return ("-" if neg else "") + "₹" + whole + "." + frac


def schedule_to_csv(
    rows: list[dict[str, int | float]], path: str | PathLike[str]
) -> None:
    """Write an amortisation schedule to a CSV file.

    Args:
        rows: Rows expected to contain the keys: month, emi, interest, principal, balance.
        path: Output CSV file path.

    Returns:
        None.
    """
    with open(path, "w") as fh:
        fh.write("month,emi,interest,principal,balance\n")
        for r in rows:
            fh.write(f'{r["month"]},{r["emi"]},{r["interest"]},{r["principal"]},{r["balance"]}\n')


def summary(
    principal: float,
    annual_rate: float,
    tenure_months: int,
    start: date | None = None,
) -> dict[str, str]:
    """Generate formatted loan metrics as a dictionary.

    This function returns a dictionary of formatted string values (not printed text).

    Args:
        principal: Loan principal.
        annual_rate: Annual interest rate as a percentage.
        tenure_months: Tenure in months.
        start: Optional start date used to compute the projected last EMI month.
            Defaults to `date.today()`. Must support `.year` and `.month`.

    Returns:
        Dictionary with keys:
        principal, rate, tenure, emi, total_interest, total_payment, last_emi, currency.
    """
    start = start or date.today()
    e = emi(principal, annual_rate, tenure_months)
    end_year = start.year + (start.month - 1 + tenure_months) // 12
    end_month = (start.month - 1 + tenure_months) % 12 + 1
    return {
        "principal": format_inr(principal),
        "rate": f"{annual_rate}% p.a.",
        "tenure": f"{tenure_months} months",
        "emi": format_inr(e),
        "total_interest": format_inr(total_interest(principal, annual_rate, tenure_months)),
        "total_payment": format_inr(total_payment(principal, annual_rate, tenure_months)),
        "last_emi": f"{end_year}-{end_month:02d}",
        "currency": DEFAULT_CURRENCY,
    }
