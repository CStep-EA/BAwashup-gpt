"""
Bower Ag CowCare Tool — R2 Storage Service
Sprint 9: Cloudflare R2 (S3-compatible) for report DOCX storage.

⚠️ Never expose R2 paths directly — always return presigned URLs.
"""

import logging
import os
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised when an R2 operation fails."""
    pass


class StorageService:
    """Cloudflare R2 storage backed by boto3 S3-compatible client."""

    def __init__(self) -> None:
        account_id = os.environ.get("R2_ACCOUNT_ID", "")
        access_key = os.environ.get("R2_ACCESS_KEY_ID", "")
        secret_key = os.environ.get("R2_SECRET_ACCESS_KEY", "")
        self.bucket = os.environ.get("R2_BUCKET_NAME", "")

        # Allow initialization even without credentials (for testing)
        self._configured = bool(account_id and access_key and secret_key and self.bucket)

        if not self._configured:
            logger.warning(
                "[R2] Credentials incomplete — storage operations will fail. "
                "Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME in .env"
            )
            self.client = None
            self.endpoint_url = ""
            return

        self.endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    def _require_configured(self) -> None:
        """Raise StorageError if R2 credentials are not configured."""
        if not self._configured or self.client is None:
            raise StorageError("R2 storage not configured — credentials missing in .env")

    async def upload_bytes(
        self,
        data: bytes,
        r2_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload bytes to R2 at the given path.

        Returns the full R2 path (not a URL — use get_presigned_url for that).
        Raises StorageError on failure.
        """
        self._require_configured()
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=r2_path,
                Body=data,
                ContentType=content_type,
            )
            logger.info(f"[R2] Uploaded {len(data)} bytes to {r2_path}")
            return r2_path
        except ClientError as e:
            raise StorageError(f"R2 upload failed for '{r2_path}': {e}")
        except Exception as e:
            raise StorageError(f"Unexpected R2 upload error: {e}")

    async def get_presigned_url(
        self,
        r2_path: str,
        expiry_seconds: int = 86400,
    ) -> str:
        """
        Generate a presigned download URL valid for expiry_seconds.
        Default: 24 hours (86400 seconds).
        """
        self._require_configured()
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": r2_path},
                ExpiresIn=expiry_seconds,
            )
            return url
        except ClientError as e:
            raise StorageError(f"R2 presigned URL failed for '{r2_path}': {e}")
        except Exception as e:
            raise StorageError(f"Unexpected R2 presigned URL error: {e}")

    async def download_to_file(self, r2_path: str, local_path: str) -> None:
        """
        Download a file from R2 to a local path.
        Sprint 14: Used by video worker to download video for frame extraction.
        """
        self._require_configured()
        try:
            self.client.download_file(self.bucket, r2_path, local_path)
            logger.info(f"[R2] Downloaded {r2_path} to {local_path}")
        except ClientError as e:
            raise StorageError(f"R2 download failed for '{r2_path}': {e}")
        except Exception as e:
            raise StorageError(f"Unexpected R2 download error: {e}")

    async def delete_file(self, r2_path: str) -> bool:
        """
        Delete a file from R2. Returns True on success, False on failure.
        Never raises — just logs and returns False.
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=r2_path)
            logger.info(f"[R2] Deleted {r2_path}")
            return True
        except Exception as e:
            logger.warning(f"[R2] Delete failed for '{r2_path}': {e}")
            return False


# ─── Singleton ────────────────────────────────────────────────────────────────

_storage: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Lazy-load singleton StorageService."""
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage
