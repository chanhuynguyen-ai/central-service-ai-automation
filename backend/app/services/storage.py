"""Small S3-compatible storage adapter used by request attachments."""
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class StorageError(Exception):
    pass


def _client(endpoint_url: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


@lru_cache
def internal_client():
    return _client(settings.s3_endpoint_url)


@lru_cache
def public_client():
    return _client(settings.s3_public_endpoint_url)


def ensure_bucket() -> None:
    client = internal_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 404 or code in {"404", "NoSuchBucket", "NotFound"}:
            client.create_bucket(Bucket=settings.s3_bucket)
            return
        raise StorageError("Object storage is unavailable") from exc


def presign_upload(*, object_key: str, mime_type: str) -> str:
    ensure_bucket()
    try:
        return public_client().generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.s3_bucket,
                "Key": object_key,
                "ContentType": mime_type,
            },
            ExpiresIn=settings.s3_presign_expiry_seconds,
            HttpMethod="PUT",
        )
    except ClientError as exc:
        raise StorageError("Could not create upload URL") from exc


def object_head(object_key: str) -> dict:
    ensure_bucket()
    try:
        return internal_client().head_object(Bucket=settings.s3_bucket, Key=object_key)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 404 or code in {"404", "NoSuchKey", "NotFound"}:
            raise StorageError("Uploaded object was not found") from exc
        raise StorageError("Could not verify uploaded object") from exc


def delete_object(object_key: str) -> None:
    try:
        internal_client().delete_object(Bucket=settings.s3_bucket, Key=object_key)
    except ClientError as exc:
        raise StorageError("Could not delete object") from exc


def presign_download(*, object_key: str, filename: str, mime_type: str) -> str:
    ensure_bucket()
    disposition = f'attachment; filename="{filename.replace(chr(34), "")}"'
    try:
        return public_client().generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.s3_bucket,
                "Key": object_key,
                "ResponseContentType": mime_type,
                "ResponseContentDisposition": disposition,
            },
            ExpiresIn=settings.s3_presign_expiry_seconds,
            HttpMethod="GET",
        )
    except ClientError as exc:
        raise StorageError("Could not create download URL") from exc
