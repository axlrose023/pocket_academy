import asyncio
import logging
from typing import Protocol

import boto3
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import SecretStr

from config import StorageConfig

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
