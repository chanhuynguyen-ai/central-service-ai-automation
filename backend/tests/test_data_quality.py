from app.services.data_quality import clean_service_request_rows


def test_data_quality_normalizes_and_flags_inconsistent_terminal_timestamp() -> None:
    rows = [
        {
            "reference": " csr-1 ",
            "title": "Example",
            "department": "Finance",
            "category": "Access Request",
            "priority": "HIGH",
            "status": "Rejected",
            "submitted_at": "2026-09-01T08:00:00Z",
            "due_at": "2026-09-01T16:00:00Z",
            "completed_at": "2026-09-01T09:00:00Z",
            "ai_confidence": "0.9",
            "within_sla": "true",
        }
    ]

    cleaned, report = clean_service_request_rows(rows)

    assert cleaned[0]["reference"] == "CSR-1"
    assert cleaned[0]["category"] == "access_request"
    assert cleaned[0]["priority"] == "high"
    assert cleaned[0]["status"] == "rejected"
    assert cleaned[0]["completed_at"] == ""
    assert report["issue_count"] == 1
    assert report["issues"][0]["issue"] == "cleared_completed_at_for_non_completed_status"


def test_data_quality_recomputes_completed_sla() -> None:
    rows = [
        {
            "reference": "CSR-2",
            "title": "Example",
            "department": "IT",
            "category": "it_support",
            "priority": "medium",
            "status": "completed",
            "submitted_at": "2026-09-01T08:00:00Z",
            "due_at": "2026-09-01T16:00:00Z",
            "completed_at": "2026-09-01T17:00:00Z",
            "ai_confidence": "0.88",
            "within_sla": "true",
        }
    ]

    cleaned, report = clean_service_request_rows(rows)

    assert cleaned[0]["within_sla"] == "false"
    assert report["completed_sla_compliance_pct"] == 0.0
