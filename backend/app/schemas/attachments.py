from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AttachmentPresignInput(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=160)
    size_bytes: int = Field(gt=0, le=10 * 1024 * 1024)
    visibility: Literal["REQUESTER_VISIBLE", "INTERNAL"] = "REQUESTER_VISIBLE"

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or cleaned in {".", ".."}:
            raise ValueError("A valid filename is required")
        if any(char in cleaned for char in ("/", "\\", "\x00")):
            raise ValueError("Filename must not contain path separators")
        if any(ord(char) < 32 or ord(char) == 127 for char in cleaned):
            raise ValueError("Filename must not contain control characters")
        return cleaned

    @field_validator("mime_type")
    @classmethod
    def normalize_mime_type(cls, value: str) -> str:
        cleaned = value.split(";", 1)[0].strip().lower()
        if not cleaned or "/" not in cleaned:
            raise ValueError("A valid MIME type is required")
        return cleaned


class AttachmentPresignOut(BaseModel):
    attachment_id: int
    upload_url: str
    upload_method: Literal["POST"] = "POST"
    form_fields: dict[str, str]
    expires_in_seconds: int


class AttachmentCompleteInput(BaseModel):
    pass


class AttachmentOut(BaseModel):
    id: int
    request_id: int
    uploaded_by: int
    uploader_name: str
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str | None
    visibility: str
    status: str
    created_at: datetime
    ready_at: datetime | None


class AttachmentDownloadOut(BaseModel):
    download_url: str
    expires_in_seconds: int
