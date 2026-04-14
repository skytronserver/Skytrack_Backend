"""
MinIO file storage backend for Skytrack.

Replaces the local HOST_STORAGE_PATH disk writes with objects stored in a
MinIO (S3-compatible) bucket.  All configuration is read from environment
variables so nothing is hard-coded here.

Environment variables (add to .env):
    MINIO_ENDPOINT   – host:port of the MinIO server, e.g. "192.168.1.10:9000"
    MINIO_ACCESS_KEY – MinIO access key / root user
    MINIO_SECRET_KEY – MinIO secret key / root password
    MINIO_BUCKET     – bucket name (created automatically if absent), e.g. "skytrack-files"
    MINIO_SECURE     – "True" to use HTTPS, "False" (default) for plain HTTP

Public API (used by views.py):
    upload_bytes(object_key, data_bytes, content_type)
    object_exists(object_key)  -> bool
    download_bytes(object_key) -> bytes
    ensure_bucket()            -> None   (called once at startup)
"""

import io
import os

from minio import Minio
from minio.error import S3Error

# ---------------------------------------------------------------------------
# Configuration – read once at module import time
# ---------------------------------------------------------------------------
_ENDPOINT   = os.environ.get('MINIO_ENDPOINT',   'localhost:9000')
_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
_BUCKET     = os.environ.get('MINIO_BUCKET',     'skytrack-files')
_SECURE     = os.environ.get('MINIO_SECURE',     'False').strip().lower() == 'true'

_client = None  # lazy-initialised


def _get_client() -> Minio:
    """Return (and lazily create) the shared MinIO client."""
    global _client
    if _client is None:
        _client = Minio(
            _ENDPOINT,
            access_key=_ACCESS_KEY,
            secret_key=_SECRET_KEY,
            secure=_SECURE,
        )
    return _client


def ensure_bucket() -> None:
    """Create the configured bucket if it does not already exist."""
    client = _get_client()
    if not client.bucket_exists(_BUCKET):
        client.make_bucket(_BUCKET)


def upload_bytes(object_key: str, data_bytes: bytes, content_type: str = 'application/octet-stream') -> None:
    """Upload *data_bytes* as *object_key* inside the configured bucket."""
    client = _get_client()
    ensure_bucket()
    data = io.BytesIO(data_bytes)
    client.put_object(
        _BUCKET,
        object_key,
        data,
        length=len(data_bytes),
        content_type=content_type,
    )


def object_exists(object_key: str) -> bool:
    """Return True if *object_key* exists in the bucket, False otherwise."""
    try:
        _get_client().stat_object(_BUCKET, object_key)
        return True
    except S3Error:
        return False


def download_bytes(object_key: str) -> bytes:
    """Download *object_key* from the bucket and return its content as bytes."""
    response = _get_client().get_object(_BUCKET, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()
