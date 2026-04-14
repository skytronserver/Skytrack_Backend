#!/usr/bin/env python3
"""
migrate_to_minio.py
-------------------
One-shot script to upload all existing files from the local HOST_STORAGE_PATH
directory into the MinIO bucket so that the application can be switched over to
the new storage backend without losing any previously uploaded files.

Usage:
    # Make sure your .env is sourced (or set the env vars manually) before running:
    source .env
    python3 migrate_to_minio.py

    # Dry-run (list what would be uploaded, no actual upload):
    DRY_RUN=1 python3 migrate_to_minio.py

    # Skip files that already exist in MinIO (safe to re-run):
    python3 migrate_to_minio.py   # (skip is ON by default)

    # Force re-upload even if the object already exists in MinIO:
    FORCE_UPLOAD=1 python3 migrate_to_minio.py

Environment variables read:
    HOST_STORAGE_PATH  – local root directory (default: /host_storage or /var/skytrack_storage)
    MINIO_ENDPOINT     – host:port of MinIO server (default: localhost:9000)
    MINIO_ACCESS_KEY   – MinIO access key          (default: minioadmin)
    MINIO_SECRET_KEY   – MinIO secret key
    MINIO_BUCKET       – target bucket name        (default: skytrack-files)
    MINIO_SECURE       – "True" for HTTPS          (default: False)
    DRY_RUN            – set to "1" to only list files, no upload
    FORCE_UPLOAD       – set to "1" to re-upload files that already exist in MinIO
"""

import io
import mimetypes
import os
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HOST_STORAGE_PATH = os.environ.get(
    'HOST_STORAGE_PATH',
    os.environ.get('STORAGE_DIR', '/var/skytrack_storage')
)
MINIO_ENDPOINT    = os.environ.get('MINIO_ENDPOINT',   'localhost:9000')
MINIO_ACCESS_KEY  = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY  = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
MINIO_BUCKET      = os.environ.get('MINIO_BUCKET',     'skytrack-files')
MINIO_SECURE      = os.environ.get('MINIO_SECURE',     'False').strip().lower() == 'true'

DRY_RUN      = os.environ.get('DRY_RUN',      '0').strip() == '1'
FORCE_UPLOAD = os.environ.get('FORCE_UPLOAD', '0').strip() == '1'

# ---------------------------------------------------------------------------
# MinIO client
# ---------------------------------------------------------------------------
try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    print("ERROR: 'minio' package not installed.  Run:  pip install minio>=7.2.0")
    sys.exit(1)

client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
)


def ensure_bucket() -> None:
    if not client.bucket_exists(MINIO_BUCKET):
        if DRY_RUN:
            print(f"[DRY-RUN] Would create bucket '{MINIO_BUCKET}'")
        else:
            client.make_bucket(MINIO_BUCKET)
            print(f"Created bucket '{MINIO_BUCKET}'")
    else:
        print(f"Bucket '{MINIO_BUCKET}' already exists.")


def object_exists(key: str) -> bool:
    try:
        client.stat_object(MINIO_BUCKET, key)
        return True
    except S3Error:
        return False


def local_path_to_object_key(local_file_path: str) -> str:
    """
    Convert an absolute local path to the MinIO object key that mirrors the
    directory structure stored by save_file().

    Example:
        /host_storage/fileuploads/notice/12345.jpg  ->  fileuploads/notice/12345.jpg
        /host_storage/notice/12345.jpg              ->  fileuploads/notice/12345.jpg
    """
    # Make the path relative to HOST_STORAGE_PATH
    rel = os.path.relpath(local_file_path, HOST_STORAGE_PATH)

    # Normalise separators to forward slash
    rel = rel.replace(os.sep, '/')

    # Ensure the key is always rooted under fileuploads/
    if not rel.startswith('fileuploads/'):
        rel = 'fileuploads/' + rel

    return rel


def upload_file(local_path: str, object_key: str) -> None:
    content_type, _ = mimetypes.guess_type(local_path)
    if not content_type:
        content_type = 'application/octet-stream'
    file_size = os.path.getsize(local_path)
    with open(local_path, 'rb') as fh:
        client.put_object(
            MINIO_BUCKET,
            object_key,
            fh,
            length=file_size,
            content_type=content_type,
        )


def main() -> None:
    if not os.path.isdir(HOST_STORAGE_PATH):
        print(f"ERROR: HOST_STORAGE_PATH '{HOST_STORAGE_PATH}' does not exist or is not a directory.")
        sys.exit(1)

    print(f"Source directory : {HOST_STORAGE_PATH}")
    print(f"Target bucket    : {MINIO_BUCKET}  @  {MINIO_ENDPOINT}")
    print(f"Dry run          : {DRY_RUN}")
    print(f"Force upload     : {FORCE_UPLOAD}")
    print()

    if not DRY_RUN:
        ensure_bucket()

    total = 0
    uploaded = 0
    skipped = 0
    errors = 0

    for dirpath, _dirnames, filenames in os.walk(HOST_STORAGE_PATH):
        for filename in filenames:
            local_path  = os.path.join(dirpath, filename)
            object_key  = local_path_to_object_key(local_path)
            total += 1

            if DRY_RUN:
                print(f"  [DRY-RUN] {local_path}  ->  {object_key}")
                uploaded += 1
                continue

            already_exists = not FORCE_UPLOAD and object_exists(object_key)
            if already_exists:
                print(f"  SKIP (exists) {object_key}")
                skipped += 1
                continue

            try:
                upload_file(local_path, object_key)
                print(f"  OK  {object_key}")
                uploaded += 1
            except Exception as exc:
                print(f"  ERR {object_key}  -- {exc}")
                errors += 1

    print()
    print("=" * 60)
    print(f"Total files found : {total}")
    print(f"Uploaded          : {uploaded}")
    print(f"Skipped (exists)  : {skipped}")
    print(f"Errors            : {errors}")

    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
