import time
from pathlib import Path

import pytest

from services.storage import (
    MaterialStorageError,
    create_local_material_signature,
    resolve_local_material_path,
    verify_local_material_signature,
)


def test_local_material_signature_is_valid_until_expiry() -> None:
    expires_at = int(time.time()) + 60
    signature = create_local_material_signature(
        storage_key="courses/ai-trading-education.pdf",
        expires_at=expires_at,
        secret="test-secret",
    )

    assert verify_local_material_signature(
        storage_key="courses/ai-trading-education.pdf",
        expires_at=expires_at,
        signature=signature,
        secret="test-secret",
    )
    assert not verify_local_material_signature(
        storage_key="courses/other.pdf",
        expires_at=expires_at,
        signature=signature,
        secret="test-secret",
    )


def test_local_material_signature_rejects_expired_link() -> None:
    expires_at = int(time.time()) - 1
    signature = create_local_material_signature(
        storage_key="courses/ai-trading-education.pdf",
        expires_at=expires_at,
        secret="test-secret",
    )

    assert not verify_local_material_signature(
        storage_key="courses/ai-trading-education.pdf",
        expires_at=expires_at,
        signature=signature,
        secret="test-secret",
    )


def test_local_material_path_cannot_escape_storage_root(tmp_path: Path) -> None:
    allowed = resolve_local_material_path(
        root=tmp_path,
        storage_key="courses/ai-trading-education.pdf",
    )
    assert allowed == tmp_path / "courses" / "ai-trading-education.pdf"

    with pytest.raises(MaterialStorageError):
        resolve_local_material_path(root=tmp_path, storage_key="../../etc/passwd")
