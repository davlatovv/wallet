"""Validation of Telegram Mini App `initData` (https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)."""
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class InvalidInitData(Exception):
    """initData is malformed, tampered with, or expired."""


@dataclass(frozen=True)
class TelegramUser:
    id: int
    username: str | None
    first_name: str | None


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int,
    now: float | None = None,
) -> TelegramUser:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InvalidInitData("missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InvalidInitData("bad signature")

    try:
        auth_date = int(pairs["auth_date"])
    except (KeyError, ValueError):
        raise InvalidInitData("missing auth_date") from None
    current = time.time() if now is None else now
    if current - auth_date > max_age_seconds:
        raise InvalidInitData("initData expired")

    try:
        user = json.loads(pairs["user"])
        return TelegramUser(
            id=int(user["id"]),
            username=user.get("username"),
            first_name=user.get("first_name"),
        )
    except (KeyError, ValueError, TypeError):
        raise InvalidInitData("missing user") from None
