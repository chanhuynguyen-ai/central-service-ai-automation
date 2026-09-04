import pytest
from pydantic import ValidationError

from app.services.llm import parse_triage_payload


def test_structured_triage_rejects_unknown_category() -> None:
    with pytest.raises(ValidationError):
        parse_triage_payload(
            '{"category":"grant_access","priority":"high","summary":"Unsafe output",'
            '"confidence":0.99}'
        )


def test_structured_triage_accepts_valid_contract() -> None:
    result = parse_triage_payload(
        '{"category":"access_request","priority":"high",'
        '"summary":"VPN access is needed for onboarding.","confidence":0.92}'
    )
    assert result.category == "access_request"
    assert result.priority == "high"
    assert result.confidence == 0.92
