from __future__ import annotations

from aidsl.runtime import _validate


def test_valid_record(expense_plan):
    record = {"merchant": "Uber", "amount": 47.5, "category": "travel"}
    assert _validate(record, expense_plan) is True


def test_missing_field(expense_plan):
    record = {"merchant": "Uber", "amount": 47.5}  # no category
    assert _validate(record, expense_plan) is False


def test_bad_enum_value(expense_plan):
    record = {"merchant": "Uber", "amount": 47.5, "category": "transportation"}
    assert _validate(record, expense_plan) is False


def test_amount_string_coercion(expense_plan):
    record = {"merchant": "Uber", "amount": "47.50", "category": "travel"}
    assert _validate(record, expense_plan) is True
    assert record["amount"] == 47.5  # coerced to float


def test_amount_not_a_number(expense_plan):
    record = {"merchant": "Uber", "amount": "not-a-number", "category": "travel"}
    assert _validate(record, expense_plan) is False


def test_extra_fields_ok(expense_plan):
    record = {
        "merchant": "Uber",
        "amount": 47.5,
        "category": "travel",
        "extra": "ignored",
    }
    assert _validate(record, expense_plan) is True


def test_empty_record(expense_plan):
    assert _validate({}, expense_plan) is False


def test_all_enum_values_accepted(expense_plan):
    for cat in ["travel", "meals", "equipment", "software", "office"]:
        record = {"merchant": "X", "amount": 1.0, "category": cat}
        assert _validate(record, expense_plan) is True
