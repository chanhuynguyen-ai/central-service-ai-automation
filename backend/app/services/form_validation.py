"""Deterministic validation shared by draft editing and future AI intake.

A partial save permits missing fields, never invalid supplied values. Required
boolean means a value is present: False is valid, just as numeric zero is valid.
No submitted form content is included in error messages or audit records.
"""
import json
import math
import re
from datetime import date
from decimal import Decimal

from pydantic import AnyHttpUrl, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.models.models import Department, User
from app.schemas.catalog import DynamicFormSchema, FormField
from app.schemas.drafts import DraftValidation, FieldIssue

HTTP_URL = TypeAdapter(AnyHttpUrl)
CURRENCY = re.compile(r"^-?\d{1,12}(?:\.\d{1,2})?$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _empty(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip()) or value == []


def _date(value: object) -> bool:
    if not isinstance(value, str) or not DATE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _valid_value(field: FormField, value: object, db: Session | None) -> bool:
    kind = field.type
    if kind in {"text", "textarea"}:
        return isinstance(value, str) and len(value) <= (5000 if kind == "textarea" else 500)
    if kind == "number":
        return type(value) in {int, float} and abs(value) <= 1e15 and math.isfinite(value)
    if kind == "currency":
        return isinstance(value, str) and CURRENCY.fullmatch(value) is not None
    if kind == "boolean":
        return type(value) is bool
    if kind == "date":
        return _date(value)
    if kind == "date_range":
        return (
            isinstance(value, dict) and set(value) == {"start", "end"}
            and _date(value["start"]) and _date(value["end"])
            and value["start"] <= value["end"]
        )
    options = {option.value for option in field.options}
    if kind == "select":
        return isinstance(value, str) and value in options
    if kind == "multi_select":
        return (
            isinstance(value, list) and len(value) <= 200
            and all(isinstance(item, str) and item in options for item in value)
            and len(set(value)) == len(value)
        )
    if kind == "url":
        if not isinstance(value, str) or len(value) > 2048:
            return False
        try:
            HTTP_URL.validate_python(value)
            return True
        except ValidationError:
            return False
    if kind in {"user_picker", "department_picker"}:
        if type(value) is not int or value <= 0 or db is None:
            return False
        entity = db.get(User if kind == "user_picker" else Department, value)
        return entity is not None and entity.is_active
    # Attachments need authorized object-storage metadata (Phase 8). Never
    # accept an arbitrary URL or claimed attachment ID in its place.
    return False


def validate_form_data(
    schema: DynamicFormSchema,
    data: dict,
    *,
    require_complete: bool,
    db: Session | None = None,
) -> tuple[dict, list[FieldIssue]]:
    fields = {field.key: field for section in schema.sections for field in section.fields}
    errors: list[FieldIssue] = []
    cleaned: dict = {}
    if len(json.dumps(data, ensure_ascii=False, allow_nan=True)) > 65536:
        return {}, [FieldIssue(field="form_data", code="too_large", message="Form data exceeds 64 KiB.")]
    for key in data.keys() - fields.keys():
        errors.append(FieldIssue(field=key, code="unknown_field", message="Field is not in this form version."))
    for key, field in fields.items():
        value = data.get(key)
        if _empty(value):
            if require_complete and field.required:
                errors.append(FieldIssue(field=key, code="required", message="This field is required."))
            continue
        if not _valid_value(field, value, db):
            code = "unsupported_attachment" if field.type == "attachment" else "invalid_value"
            errors.append(FieldIssue(field=key, code=code, message=f"Invalid value for {field.label}."))
            continue
        cleaned[key] = format(Decimal(value), ".2f") if field.type == "currency" else value
    return cleaned, errors


def validate_draft(
    title: str, description: str, schema: DynamicFormSchema, data: dict,
    *, db: Session | None = None, validation_schema: dict | None = None,
) -> DraftValidation:
    _, errors = validate_form_data(schema, data, require_complete=True, db=db)
    if len(title.strip()) < 5:
        errors.append(FieldIssue(field="title", code="required", message="Enter at least 5 characters."))
    if len(description.strip()) < 15:
        errors.append(FieldIssue(field="description", code="required", message="Enter at least 15 characters."))
    if validation_schema:
        errors.append(FieldIssue(
            field="form_data", code="unsupported_validation_schema",
            message="This service uses additional validation rules not supported by this editor yet.",
        ))
    return DraftValidation(
        valid=not errors, errors=errors,
        missing_fields=[error.field for error in errors if error.code == "required"],
    )
