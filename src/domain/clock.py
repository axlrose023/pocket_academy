import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime.datetime: ...


class SystemClock:
    def now(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.UTC)
