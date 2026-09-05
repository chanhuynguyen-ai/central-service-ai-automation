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
        return cleaned


class AttachmentPresignOut(BaseModel):
    attachment_id: int
    upload_url: str
    upload_method: Literal["PUT"] = "PUT"
    required_headers: dict[str, str]
    expires_in_seconds: int


class AttachmentCompleteInput(BaseModel):
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")


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
