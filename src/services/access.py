from dataclasses import dataclass
from decimal import Decimal

from database.models import User
from database.uow import UnitOfWork
from domain.statuses import StatusPolicy, resolve_status


@dataclass(frozen=True, slots=True)
class UserAccessSnapshot:
    total_deposits: Decimal
    status_policy: StatusPolicy
    is_blocked: bool


class AccessService:
    async def snapshot(self, uow: UnitOfWork, *, user: User) -> UserAccessSnapshot:
        total_deposits = await uow.finance.total_deposits(user.id)
        unresolved_withdrawals = await uow.finance.unresolved_withdrawals(user.id)
        is_withdrawal_blocked = bool(unresolved_withdrawals)
        if unresolved_withdrawals:
            first_requested_at = min(
                withdrawal.requested_at for withdrawal in unresolved_withdrawals
            )
            deposits_after = await uow.finance.deposits_after(
                user.id, first_requested_at
            )
            withdrawals_total = sum(
                (withdrawal.amount for withdrawal in unresolved_withdrawals),
                start=Decimal("0"),
            )
            is_withdrawal_blocked = deposits_after < withdrawals_total
        return UserAccessSnapshot(
            total_deposits=total_deposits,
            status_policy=resolve_status(total_deposits),
            is_blocked=user.is_manually_blocked or is_withdrawal_blocked,
        )
