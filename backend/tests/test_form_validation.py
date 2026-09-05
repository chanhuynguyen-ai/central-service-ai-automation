import pytest
from pydantic import ValidationError

from app.schemas.catalog import DynamicFormSchema, RequestTypeUpdate, RequestTypeVersionUpdate
from app.services.form_validation import validate_draft, validate_form_data


def form(kind="text", required=True, options=None):
    field = {"key": "value", "label": "Value", "type": kind, "required": required}
    if options is not None:
        field["options"] = options
    return DynamicFormSchema.model_validate({"sections": [{"title": "Details", "fields": [field]}]})


@pytest.mark.parametrize(("kind", "value"), [
    ("text", "hello"), ("textarea", "details"), ("number", 0), ("number", 12.25),
    ("boolean", False), ("boolean", True), ("currency", "1200.50"),
    ("date", "2026-02-28"), ("date_range", {"start": "2026-01-01", "end": "2026-01-02"}),
    ("url", "https://example.com/policy"),
])
def test_valid_typed_values(kind, value):
    cleaned, errors = validate_form_data(form(kind), {"value": value}, require_complete=True)
    assert errors == []
    assert cleaned["value"] == value


@pytest.mark.parametrize(("kind", "value"), [
    ("text", {"nested": "value"}), ("text", "x" * 501), ("number", True),
    ("number", "10"), ("number", float("inf")), ("number", 10 ** 1000),
    ("boolean", "false"), ("currency", 10.1), ("currency", "1.234"),
    ("date", "2026-02-30"), ("date", "20260228"),
    ("date_range", {"start": "2026-03-02", "end": "2026-03-01"}),
    ("date_range", {"start": "2026-01-01"}), ("url", "javascript:alert(1)"),
    ("attachment", ["unverified-upload"]), ("user_picker", True),
])
def test_invalid_supplied_values_are_rejected_even_for_partial_save(kind, value):
    _, errors = validate_form_data(form(kind), {"value": value}, require_complete=False)
    assert len(errors) == 1


def test_partial_save_differs_from_completion_validation():
    assert validate_form_data(form(), {}, require_complete=False) == ({}, [])
    validation = validate_draft("Valid title", "Sufficient description text", form(), {})
    assert not validation.valid
    assert validation.missing_fields == ["value"]


def test_unknown_fields_and_select_membership():
    options = [{"label": "A", "value": "a"}]
    _, errors = validate_form_data(form("select", options=options), {"value": "b", "admin": True}, require_complete=True)
    assert {error.code for error in errors} == {"unknown_field", "invalid_value"}
    _, errors = validate_form_data(form("multi_select", options=options), {"value": ["a", "a"]}, require_complete=True)
    assert errors


def test_currency_uses_decimal_string_without_float_rounding():
    cleaned, errors = validate_form_data(form("currency"), {"value": "123456789012.1"}, require_complete=True)
    assert not errors
    assert cleaned["value"] == "123456789012.10"


def test_unknown_advanced_validation_rules_fail_closed():
    result = validate_draft("Valid title", "Long enough description", form(), {"value": "yes"}, validation_schema={"required": ["other"]})
    assert not result.valid
    assert result.errors[0].code == "unsupported_validation_schema"


def test_invalid_schema_options_and_null_updates():
    with pytest.raises(ValidationError):
        form("select")
    with pytest.raises(ValidationError):
        form("select", options=[{"value": "a", "label": "A"}, {"value": "a", "label": "Again"}])
    with pytest.raises(ValidationError):
        RequestTypeVersionUpdate(form_schema=None)
    with pytest.raises(ValidationError):
        RequestTypeUpdate(is_active=None)
