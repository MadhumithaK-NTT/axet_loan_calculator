import math
from datetime import date
from pathlib import Path

import pytest

# Ensure we can import the package as it exists in this repo layout.
# Repository structure: loan-calc/loan_calc/...
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # loan-calc/

from loan_calc import (  # noqa: E402
    amortisation_schedule,
    compare_offers,
    eligible_amount,
    emi,
    format_inr,
    prepayment_savings,
    remaining_tenure,
    schedule_to_csv,
    outstanding_after,
    summary,
)


def test_emi_reference_value_1m_9p_240m():
    assert emi(1_000_000, 9.0, 240) == pytest.approx(8_997.0, abs=1.0)


def test_emi_zero_interest_equals_principal_div_tenure():
    expected = round(500_000 / 120, 2)
    assert emi(500_000, 0.0, 120) == pytest.approx(expected, abs=1e-9)


def test_zero_interest_schedule_interest_is_zero_and_balances_non_negative():
    rows = amortisation_schedule(200_000, 0.0, 12)
    assert rows, "Expected at least one schedule row"
    for r in rows:
        assert r["interest"] == pytest.approx(0.0, abs=1e-9)
        assert r["balance"] >= -1e-9


def test_one_month_loan_emi_approx_and_schedule_single_row_and_final_balance_zero():
    assert emi(100_000, 12.0, 1) == pytest.approx(101_000.0, abs=1e-6)

    rows = amortisation_schedule(100_000, 12.0, 1)
    assert len(rows) == 1

    # final row balance approximately zero
    assert rows[-1]["balance"] == pytest.approx(0.0, abs=1e-6)


def test_very_large_principal_emi_positive_and_finite():
    amount = emi(9_500_000_000, 8.75, 360)
    assert amount > 0
    assert math.isfinite(amount)


def test_amortisation_schedule_correctness_len_schema_and_final_balance_zero():
    principal = 100_000
    annual_rate = 10.0
    tenure_months = 24
    rows = amortisation_schedule(principal, annual_rate, tenure_months)

    assert len(rows) == tenure_months
    assert rows[-1]["balance"] == pytest.approx(0.0, abs=1e-6)

    expected_keys = {"month", "emi", "interest", "principal", "balance"}
    for r in rows:
        assert set(r.keys()) == expected_keys
        assert r["month"] >= 1
        assert r["emi"] >= 0
        assert r["interest"] >= 0
        assert r["principal"] >= 0
        assert r["balance"] >= -1e-9


def test_outstanding_after_months_paid_zero_returns_rounded_principal():
    principal = 123_456.78
    assert outstanding_after(principal, 9.0, 120, months_paid=0) == pytest.approx(
        round(principal, 2), abs=1e-6
    )


def test_outstanding_after_after_one_payment_decreases_and_non_negative():
    principal = 200_000
    outstanding = outstanding_after(principal, 9.0, 24, months_paid=1)
    assert outstanding >= 0
    assert outstanding < principal


def test_outstanding_after_after_full_tenure_approximately_zero():
    principal = 300_000
    tenure_months = 60
    outstanding = outstanding_after(principal, 10.0, tenure_months, months_paid=tenure_months)
    assert outstanding == pytest.approx(0.0, abs=1e-6)


def test_remaining_tenure_consistency_same_principal_repays_over_original_tenure():
    principal = 200_000
    annual_rate = 9.0
    tenure_months = 240
    instalment = emi(principal, annual_rate, tenure_months)
    months = remaining_tenure(principal, annual_rate, instalment)
    assert tenure_months <= months <= tenure_months + 1


def test_remaining_tenure_balance_non_positive_returns_zero():
    assert remaining_tenure(0.0, 9.0, 1000.0) == 0
    assert remaining_tenure(-10.0, 9.0, 1000.0) == 0


def test_excessive_prepayment_pays_off_without_negative_balance_or_savings():
    principal = 1_000_000
    annual_rate = 9.0
    tenure_months = 60
    prepay_month = 6
    prepay_amount = 10_000_000

    result = prepayment_savings(
        principal=principal,
        annual_rate=annual_rate,
        tenure_months=tenure_months,
        prepay_month=prepay_month,
        prepay_amount=prepay_amount,
    )

    assert result["new_tenure"] == prepay_month
    assert result["months_saved"] >= 0
    assert result["interest_saved"] >= 0
    assert result["new_tenure"] <= tenure_months


def test_compare_offers_sorted_by_total_cost_ascending_and_required_keys():
    principal = 1_000_000
    offers = [
        {"bank": "A", "rate": 9.0, "tenure": 240, "processing_fee_pct": 1.0},
        {"bank": "B", "rate": 9.5, "tenure": 240, "processing_fee_pct": 0.0},
        {"bank": "C", "rate": 8.75, "tenure": 300},
    ]
    out = compare_offers(principal, offers)

    required_keys = {"bank", "emi", "total_interest", "processing_fee", "total_cost"}
    for item in out:
        assert set(item.keys()) == required_keys

    for i in range(len(out) - 1):
        assert out[i]["total_cost"] <= out[i + 1]["total_cost"]


def test_eligible_amount_returns_zero_when_capacity_non_positive():
    assert eligible_amount(
        monthly_income=20_000,
        existing_emis=15_000,
        annual_rate=9.0,
        tenure_months=24,
        foir=0.5,
    ) == 0.0


def test_format_inr_indian_grouping_and_negative_sign():
    assert format_inr(1234567.89) == "₹12,34,567.89"
    assert format_inr(-10.2) == "-₹10.20"


def test_schedule_to_csv_writes_expected_header_and_single_row(tmp_path):
    csv_path = tmp_path / "schedule.csv"
    rows = [
        {
            "month": 1,
            "emi": 1000.0,
            "interest": 50.0,
            "principal": 950.0,
            "balance": 99_050.0,
        }
    ]

    schedule_to_csv(rows, str(csv_path))

    content = csv_path.read_text(encoding="utf-8").splitlines()
    assert content[0] == "month,emi,interest,principal,balance"

    # Verify the single written data row
    assert content[1] == "1,1000.0,50.0,950.0,99050.0"


def test_summary_returns_expected_keys_all_string_values_and_last_emi():
    result = summary(
        principal=100_000,
        annual_rate=9.0,
        tenure_months=12,
        start=date(2026, 1, 1),
    )
    expected_keys = {
        "principal",
        "rate",
        "tenure",
        "emi",
        "total_interest",
        "total_payment",
        "last_emi",
        "currency",
    }
    assert set(result.keys()) == expected_keys
    assert all(isinstance(v, str) for v in result.values())
    assert result["last_emi"] == "2027-01"

