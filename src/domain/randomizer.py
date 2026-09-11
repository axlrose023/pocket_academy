import random
from typing import Protocol

from domain.enums import SignalDirection
from domain.statuses import StatusPolicy


class RandomSource(Protocol):
    def choice[T](self, sequence: tuple[T, ...]) -> T: ...

    def randint(self, lower: int, upper: int) -> int: ...


class SignalRandomizer:
    def __init__(self, random_source: RandomSource | None = None) -> None:
        self._random = random_source or random.SystemRandom()

    def direction(self) -> SignalDirection:
        return self._random.choice((SignalDirection.BUY, SignalDirection.SELL))

    def probability(self, policy: StatusPolicy, *, premium: bool) -> int:
        if premium:
            return self._random.randint(96, 97)
        return self._random.randint(policy.probability_min, policy.probability_max)
