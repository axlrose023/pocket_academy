import datetime

import pytest

from domain.enums import ExternalEventType, WithdrawalStatus
from services.exceptions import UnsupportedExternalEventError
from services.external_events import ChatterflyLeadParser, PocketOptionEventParser


class FixedClock:
    def now(self) -> datetime.datetime:
        return datetime.datetime(2026, 9, 22, 12, 0, tzinfo=datetime.UTC)


def test_chatterfly_lead_uses_real_macro_aliases() -> None:
    lead = ChatterflyLeadParser(FixedClock()).parse(
        {
            "event": "lead",
            "chatId": "8481190128",
            "tracker.clickid": "click-123",
            "username": "@academy_user",
            "created_at": "2026-09-22T10:00:00Z",
        }
    )

    assert lead.telegram_id == 8481190128
    assert lead.click_id == "click-123"
    assert lead.username == "academy_user"
    assert lead.occurred_at == datetime.datetime(
        2026, 9, 22, 10, 0, tzinfo=datetime.UTC
    )


@pytest.mark.parametrize(
    ("telegram_id", "click_id"),
    [
        ("not-a-number", "click-123"),
        ("8481190128", "{{tracker.clickid}}"),
        ("8481190128", ""),
    ],
)
def test_chatterfly_lead_rejects_unresolved_or_invalid_identifiers(
    telegram_id: str,
    click_id: str,
) -> None:
    with pytest.raises(UnsupportedExternalEventError):
        ChatterflyLeadParser(FixedClock()).parse(
            {
                "event": "lead",
                "chatId": telegram_id,
                "tracker.clickid": click_id,
            }
        )


@pytest.mark.parametrize(
    ("raw_event", "expected_event"),
    [
        ("registration", ExternalEventType.REGISTRATION),
        ("sale", ExternalEventType.FIRST_DEPOSIT),
        ("resale", ExternalEventType.REPEAT_DEPOSIT),
    ],
)
def test_pocket_parser_accepts_chatterfly_event_names(
    raw_event: str,
    expected_event: ExternalEventType,
) -> None:
    payload = {
        "tracker.event": raw_event,
        "clickid": "click-123",
        "trader_id": "trader-42",
        "date_time": "2026-09-22T11:00:00Z",
    }
    if raw_event != "registration":
        payload["sumdep"] = "50.25"

    postback = PocketOptionEventParser(FixedClock()).parse(payload)

    assert postback.event_type == expected_event
    assert postback.trader_id == "trader-42"


def test_successful_withdrawal_without_provider_transaction_id_is_stable() -> None:
    payload = {
        "event": "successful_withdrawal",
        "trader_id": "trader-42",
        "wdr_sum": "10.00",
        "date_time": "2026-09-22T11:30:00Z",
    }
    parser = PocketOptionEventParser(FixedClock())

    first = parser.parse(payload)
    second = parser.parse(payload)

    assert first.event_type == ExternalEventType.WITHDRAWAL
    assert first.withdrawal_status == WithdrawalStatus.SUCCESS
    assert first.withdrawal_reference == second.withdrawal_reference
    assert first.withdrawal_reference is not None
    assert first.withdrawal_reference.startswith("derived-")
