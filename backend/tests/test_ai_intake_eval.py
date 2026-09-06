import json
from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import login

EVAL_CASES = Path(__file__).resolve().parents[1] / "evals" / "ai_intake_cases.json"

SERVICE_DEFINITIONS = [
    {
        "code": "IT_LAPTOP_REPLACEMENT",
        "category": "IT",
        "title": "Laptop replacement",
        "description": "Request a managed replacement device for your work.",
        "required": {"reason", "device", "cost_center"},
        "fields": [
            {"key": "reason", "type": "textarea", "label": "Reason for replacement", "required": True},
            {
                "key": "device",
                "type": "select",
                "label": "Preferred device",
                "required": True,
                "options": [
                    {"value": "windows", "label": "Windows laptop"},
                    {"value": "macos", "label": "MacBook"},
                ],
            },
            {"key": "cost_center", "type": "text", "label": "Cost center", "required": True},
            {"key": "needed_by", "type": "date", "label": "Needed by"},
        ],
    },
    {
        "code": "IT_SOFTWARE_ACCESS",
        "category": "IT",
        "title": "Software access",
        "description": "Explain the application and access level needed for your work.",
        "required": {"application", "access_level", "justification", "temporary"},
        "fields": [
            {"key": "application", "type": "text", "label": "Application", "required": True},
            {
                "key": "access_level",
                "type": "select",
                "label": "Access level",
                "required": True,
                "options": [
                    {"value": "standard", "label": "Standard user"},
                    {"value": "elevated", "label": "Elevated access"},
                ],
            },
            {"key": "justification", "type": "textarea", "label": "Business justification", "required": True},
            {"key": "temporary", "type": "boolean", "label": "Temporary access?", "required": True},
        ],
    },
    {
        "code": "FINANCE_REIMBURSEMENT",
        "category": "Finance",
        "title": "Expense reimbursement",
        "description": "Record business expenses for reimbursement.",
        "required": {"amount", "currency", "expense_date", "purpose"},
        "fields": [
            {"key": "amount", "type": "currency", "label": "Amount", "required": True},
            {
                "key": "currency",
                "type": "select",
                "label": "Currency",
                "required": True,
                "options": [
                    {"value": "VND", "label": "VND"},
                    {"value": "USD", "label": "USD"},
                ],
            },
            {"key": "expense_date", "type": "date", "label": "Expense date", "required": True},
            {"key": "purpose", "type": "textarea", "label": "Business purpose", "required": True},
        ],
    },
]


def _seed_eval_catalog(client: TestClient) -> None:
    admin = login(client, "admin")
    for service in SERVICE_DEFINITIONS:
        created = client.post(
            "/api/v1/catalog/request-types",
            headers=admin,
            json={
                "code": service["code"],
                "category": service["category"],
                "is_active": True,
            },
        )
        assert created.status_code == 201
        request_type_id = created.json()["id"]
        version = client.post(
            f"/api/v1/catalog/request-types/{request_type_id}/versions",
            headers=admin,
            json={
                "title": service["title"],
                "description": service["description"],
                "form_schema": {
                    "sections": [
                        {
                            "title": "Request details",
                            "fields": service["fields"],
                        }
                    ]
                },
            },
        )
        assert version.status_code == 201
        published = client.post(
            f"/api/v1/catalog/request-types/{request_type_id}/versions/1/publish",
            headers=admin,
        )
        assert published.status_code == 200


def test_ai_intake_evaluation_corpus_meets_quality_gates(client: TestClient) -> None:
    _seed_eval_catalog(client)
    employee = login(client, "employee")
    cases = json.loads(EVAL_CASES.read_text(encoding="utf-8"))
    required_by_code = {item["code"]: item["required"] for item in SERVICE_DEFINITIONS}

    top1_correct = 0
    top2_correct = 0
    expected_field_total = 0
    expected_field_correct = 0
    missing_field_correct = 0

    for case in cases:
        classified = client.post(
            "/api/v1/ai/intake/classify",
            headers=employee,
            json={"text": case["text"]},
        )
        assert classified.status_code == 200
        classification = classified.json()
        expected_code = case["request_type_code"]
        top1_correct += classification["request_type_code"] == expected_code
        ranked_codes = [classification["request_type_code"]] + [
            item["request_type_code"] for item in classification["alternatives"]
        ]
        top2_correct += expected_code in ranked_codes[:2]
        assert classification["needs_human_confirmation"] is True

        drafted = client.post(
            "/api/v1/ai/intake/draft",
            headers=employee,
            json={"text": case["text"], "request_type_code": expected_code},
        )
        assert drafted.status_code == 200
        suggestion = drafted.json()
        assert suggestion["request_type_code"] == expected_code
        assert suggestion["needs_human_confirmation"] is True

        for field, expected_value in case.get("expected_fields", {}).items():
            expected_field_total += 1
            expected_field_correct += suggestion["extracted_fields"].get(field) == expected_value

        expected_missing = sorted(required_by_code[expected_code] - suggestion["extracted_fields"].keys())
        missing_field_correct += sorted(suggestion["missing_required_fields"]) == expected_missing

    total = len(cases)
    classification_accuracy = top1_correct / total
    top2_accuracy = top2_correct / total
    extraction_accuracy = expected_field_correct / max(1, expected_field_total)
    missing_field_accuracy = missing_field_correct / total

    print(
        "AI intake eval: "
        f"top1={classification_accuracy:.3f}, "
        f"top2={top2_accuracy:.3f}, "
        f"extraction={extraction_accuracy:.3f}, "
        f"missing={missing_field_accuracy:.3f}, cases={total}"
    )
    assert total >= 30
    assert classification_accuracy >= 0.90
    assert top2_accuracy >= 0.95
    assert extraction_accuracy >= 0.90
    assert missing_field_accuracy == 1.0
