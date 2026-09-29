import asyncio
import hashlib
import hmac
import logging
import time
from pathlib import Path
from typing import Protocol
from urllib.parse import urlencode

import boto3
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import SecretStr

from config import ApiConfig, StorageConfig

logger = logging.getLogger(__name__)


class MaterialStorageError(RuntimeError):
    pass


class MaterialStorage(Protocol):
    async def download_url(self, storage_key: str | None) -> str | None: ...


class DisabledMaterialStorage:
    async def download_url(self, storage_key: str | None) -> str | None:
        return None


class S3MaterialStorage:
    def __init__(self, config: StorageConfig) -> None:
        self._bucket = _required_bucket(config)
        self._expires_in = config.presigned_download_ttl_seconds
        credentials = _credentials(config)
        self._client = boto3.client(
            "s3",
            endpoint_url=_optional_value(config.endpoint_url),
            region_name=config.region.strip(),
            config=BotocoreConfig(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
                s3={
                    "addressing_style": ("path" if config.force_path_style else "auto")
                },
            ),
            **credentials,
        )

    async def download_url(self, storage_key: str | None) -> str | None:
        if storage_key is None or not storage_key.strip():
            return None
        try:
            return await asyncio.to_thread(
                self._create_download_url,
                storage_key.strip(),
            )
        except (BotoCoreError, ClientError, ValueError) as error:
            logger.warning("Could not create S3 material URL: %s", error)
            raise MaterialStorageError(
                "Material storage is temporarily unavailable"
            ) from error

    def close(self) -> None:
        self._client.close()

    def _create_download_url(self, storage_key: str) -> str:
        return self._client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self._bucket, "Key": storage_key},
            ExpiresIn=self._expires_in,
            HttpMethod="GET",
        )


class LocalMaterialStorage:
    """Creates short-lived links for private files stored in the app volume."""

    def __init__(self, storage: StorageConfig, api: ApiConfig) -> None:
        if not storage.local_enabled:
            raise MaterialStorageError("Local material storage is disabled")
        if api.public_base_url is None or not api.public_base_url.strip():
            raise MaterialStorageError(
                "API public base URL is required for local material storage"
            )
        secret = _secret_value(storage.local_download_secret)
        if secret is None:
            raise MaterialStorageError("Local material storage secret is not configured")
        self._public_base_url = api.public_base_url.rstrip("/")
        self._secret = secret
        self._ttl_seconds = storage.local_download_ttl_seconds

    async def download_url(self, storage_key: str | None) -> str | None:
        if storage_key is None or not storage_key.strip():
            return None
        normalized_key = storage_key.strip()
        expires_at = int(time.time()) + self._ttl_seconds
        signature = create_local_material_signature(
            storage_key=normalized_key,
            expires_at=expires_at,
            secret=self._secret,
        )
        query = urlencode(
            {"key": normalized_key, "expires": expires_at, "signature": signature}
        )
        return f"{self._public_base_url}/api/materials/download?{query}"


def create_local_material_signature(
    *, storage_key: str, expires_at: int, secret: str
) -> str:
    payload = f"{storage_key}:{expires_at}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_local_material_signature(
    *, storage_key: str, expires_at: int, signature: str, secret: str
) -> bool:
    if expires_at < int(time.time()):
        return False
    expected = create_local_material_signature(
        storage_key=storage_key,
        expires_at=expires_at,
        secret=secret,
    )
    return hmac.compare_digest(signature, expected)


def resolve_local_material_path(*, root: Path, storage_key: str) -> Path:
    """Resolve a material key without allowing a path to escape its storage root."""
    base = root.resolve()
    candidate = (base / storage_key).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as error:
        raise MaterialStorageError("Invalid material key") from error
    return candidate


def _required_bucket(config: StorageConfig) -> str:
    if config.bucket is None or not config.bucket.strip():
        raise MaterialStorageError("S3 bucket is not configured")
    return config.bucket.strip()


def _credentials(config: StorageConfig) -> dict[str, str]:
    access_key_id = _secret_value(config.access_key_id)
    secret_access_key = _secret_value(config.secret_access_key)
    if access_key_id is None or secret_access_key is None:
        return {}
    return {
        "aws_access_key_id": access_key_id,
        "aws_secret_access_key": secret_access_key,
    }


def _secret_value(value: SecretStr | None) -> str | None:
    if value is None:
        return None
    resolved_value = value.get_secret_value().strip()
    return resolved_value or None


def _optional_value(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None
