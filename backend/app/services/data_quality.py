import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

ALLOWED_PRIORITIES = {"low", "medium", "high", "urgent"}
ALLOWED_STATUSES = {"pending_approval", "in_progress", "completed", "rejected", "cancelled"}


def parse_datetime(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def clean_service_request_rows(rows: Iterable[dict[str, str]]) -> tuple[list[dict[str, str]], dict]:
    cleaned: list[dict[str, str]] = []
    issues: list[dict[str, object]] = []
    seen_references: set[str] = set()

    for row_number, raw in enumerate(rows, start=2):
        row = {key: (value or "").strip() for key, value in raw.items()}
        reference = row.get("reference", "").upper()
        row["reference"] = reference
        row["category"] = row.get("category", "").lower().replace(" ", "_")
        row["priority"] = row.get("priority", "").lower()
        row["status"] = row.get("status", "").lower().replace(" ", "_")

        if not reference:
            issues.append({"row": row_number, "field": "reference", "issue": "missing_reference"})
        elif reference in seen_references:
            issues.append({"row": row_number, "field": "reference", "issue": "duplicate_reference", "value": reference})
        seen_references.add(reference)

        for required in ("title", "department", "category"):
            if not row.get(required):
                issues.append({"row": row_number, "field": required, "issue": "missing_required_value"})

        if row["priority"] not in ALLOWED_PRIORITIES:
            issues.append({"row": row_number, "field": "priority", "issue": "invalid_priority", "value": row["priority"]})
        if row["status"] not in ALLOWED_STATUSES:
            issues.append({"row": row_number, "field": "status", "issue": "invalid_status", "value": row["status"]})

        try:
            confidence = float(row.get("ai_confidence", ""))
            if not 0 <= confidence <= 1:
                raise ValueError
            row["ai_confidence"] = f"{confidence:.2f}"
        except ValueError:
            issues.append({"row": row_number, "field": "ai_confidence", "issue": "invalid_confidence", "value": row.get("ai_confidence", "")})

        submitted = due = completed = None
        for field in ("submitted_at", "due_at", "completed_at"):
            try:
                parsed = parse_datetime(row.get(field, ""))
                if field == "submitted_at":
                    submitted = parsed
                elif field == "due_at":
                    due = parsed
                else:
                    completed = parsed
            except ValueError:
                issues.append({"row": row_number, "field": field, "issue": "invalid_datetime", "value": row.get(field, "")})

        if submitted and due and due < submitted:
            issues.append({"row": row_number, "field": "due_at", "issue": "due_before_submission"})

        if row["status"] != "completed" and completed is not None:
            issues.append({
                "row": row_number,
                "field": "completed_at",
                "issue": "cleared_completed_at_for_non_completed_status",
                "previous_value": row["completed_at"],
            })
            row["completed_at"] = ""
            completed = None

        if row["status"] == "completed" and completed is None:
            issues.append({"row": row_number, "field": "completed_at", "issue": "missing_completed_at"})

        if row["status"] == "completed" and completed and due:
            row["within_sla"] = "true" if completed <= due else "false"
        else:
            row["within_sla"] = "true" if parse_bool(row.get("within_sla", "")) else "false"

        cleaned.append(row)

    category_counts = Counter(row.get("category", "unknown") for row in cleaned)
    completed_rows = [row for row in cleaned if row.get("status") == "completed"]
    completed_within_sla = sum(parse_bool(row.get("within_sla", "")) for row in completed_rows)
    report = {
        "rows_read": len(cleaned),
        "issue_count": len(issues),
        "issues": issues,
        "category_counts": dict(sorted(category_counts.items())),
        "completed_requests": len(completed_rows),
        "completed_sla_compliance_pct": round(
            completed_within_sla / len(completed_rows) * 100, 1
        ) if completed_rows else 100.0,
    }
    return cleaned, report


def clean_csv(input_path: Path, output_path: Path, report_path: Path) -> dict:
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        cleaned, report = clean_service_request_rows(reader)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
