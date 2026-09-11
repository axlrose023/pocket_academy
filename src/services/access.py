from dataclasses import dataclass
from decimal import Decimal

from database.dao.finance_dao import WithdrawalCoverage
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
        withdrawal_coverages = await uow.finance.unresolved_withdrawal_coverages(
            user.id
        )
        is_withdrawal_blocked = self._is_withdrawal_blocked(withdrawal_coverages)
        if user.is_manually_blocked:
            is_blocked = True
        elif user.is_manually_unblocked:
            is_blocked = False
        else:
            is_blocked = is_withdrawal_blocked
        return UserAccessSnapshot(
            total_deposits=total_deposits,
            status_policy=resolve_status(total_deposits),
            is_blocked=is_blocked,
        )

    @staticmethod
    def _is_withdrawal_blocked(
        withdrawal_coverages: list[WithdrawalCoverage],
    ) -> bool:
        unresolved_amount = Decimal("0")
        for coverage in sorted(
            withdrawal_coverages,
            key=lambda item: (item.withdrawal.requested_at, str(item.withdrawal.id)),
            reverse=True,
        ):
            unresolved_amount += coverage.withdrawal.amount
            if coverage.deposits_after < unresolved_amount:
                return True
        return False
