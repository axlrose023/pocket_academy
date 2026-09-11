class TelegramInitDataError(ValueError):
    """Raised when a Telegram Mini App credential is malformed or untrusted."""


class UnsupportedExternalEventError(ValueError):
    """Raised when a provider event cannot be safely classified yet."""
