import hmac

from fastapi import HTTPException, Request, status
from pydantic import SecretStr


def require_webhook_secret(
    request: Request, configured_secret: SecretStr | None
) -> None:
    if configured_secret is None or not configured_secret.get_secret_value().strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integration is not configured",
        )
    received_secret = request.headers.get(
        "X-Webhook-Secret"
    ) or request.query_params.get(
        "token",
    )
    if received_secret is None or not hmac.compare_digest(
        received_secret,
        configured_secret.get_secret_value(),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook credentials",
        )
