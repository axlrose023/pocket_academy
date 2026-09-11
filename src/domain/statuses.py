from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class UserStatus(StrEnum):
    NOVICE = "novice"
    TRADER = "trader"
    PROFESSIONAL = "professional"
    EXPERT = "expert"
    MASTER = "master"
    LEGEND = "legend"


@dataclass(frozen=True, slots=True)
class StatusPolicy:
    status: UserStatus
    minimum_deposits: Decimal
    minimum_timeframe_seconds: int
    signal_wait_seconds: int
    probability_min: int
    probability_max: int
    daily_signal_limit: int | None


STATUS_POLICIES = (
    StatusPolicy(UserStatus.NOVICE, Decimal("0"), 1_200, 300, 70, 75, 8),
    StatusPolicy(UserStatus.TRADER, Decimal("50"), 600, 180, 78, 82, 12),
    StatusPolicy(UserStatus.PROFESSIONAL, Decimal("150"), 60, 60, 83, 87, 20),
    StatusPolicy(UserStatus.EXPERT, Decimal("300"), 30, 60, 90, 92, 50),
    StatusPolicy(UserStatus.MASTER, Decimal("1000"), 30, 30, 92, 95, 100),
    StatusPolicy(UserStatus.LEGEND, Decimal("5000"), 30, 5, 95, 98, None),
)

TIMEFRAMES_SECONDS = (5, 30, 60, 180, 300, 600, 900, 1200, 1500, 1800, 2400, 2700, 3600)


def resolve_status(total_deposits: Decimal) -> StatusPolicy:
    return next(
        policy
        for policy in reversed(STATUS_POLICIES)
        if total_deposits >= policy.minimum_deposits
    )


def allowed_timeframes(policy: StatusPolicy) -> tuple[int, ...]:
    return tuple(
        timeframe
        for timeframe in TIMEFRAMES_SECONDS
        if timeframe >= policy.minimum_timeframe_seconds
    )
