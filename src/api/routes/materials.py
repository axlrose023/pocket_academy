import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from services.storage import (
    MaterialStorageError,
    resolve_local_material_path,
    verify_local_material_signature,
)

router = APIRouter(tags=["materials"])


@router.get("/materials/download", include_in_schema=False)
async def download_local_material(
    request: Request,
    storage_key: str = Query(alias="key", min_length=1, max_length=1_024),
    expires_at: int = Query(alias="expires", ge=0),
    signature: str = Query(min_length=64, max_length=64),
) -> FileResponse:
    storage = request.app.state.config.storage
    secret = storage.local_download_secret
    if not storage.local_enabled or secret is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if not verify_local_material_signature(
        storage_key=storage_key,
        expires_at=expires_at,
        signature=signature,
        secret=secret.get_secret_value(),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Material link is invalid or expired",
        )

    try:
        material_path = resolve_local_material_path(
            root=storage.local_directory,
            storage_key=storage_key,
        )
    except MaterialStorageError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error

    if not material_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    media_type = mimetypes.guess_type(material_path.name)[0] or "application/octet-stream"
    return FileResponse(
        Path(material_path),
        media_type=media_type,
        headers={"Cache-Control": "private, no-store"},
    )
