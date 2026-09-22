class TelegramInitDataError(ValueError):
    """Raised when a Telegram Mini App credential is malformed or untrusted."""


class UnsupportedExternalEventError(ValueError):
    """Raised when a provider event cannot be safely classified yet."""


class AttributionConflictError(ValueError):
    """Raised when a click ID is already assigned to another Telegram user."""


class PocketOptionLinkError(ValueError):
    """Raised when a Pocket Option registration link cannot be issued."""


class PocketOptionLinkConfigurationError(PocketOptionLinkError):
    """Raised when the Pocket Option registration link is unavailable."""


class ReregistrationUnavailableError(PocketOptionLinkError):
    """Raised when the user cannot receive a new Pocket Option link yet."""
