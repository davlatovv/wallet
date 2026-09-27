from datetime import datetime, timedelta, timezone

import jwt

_ALGORITHM = "HS256"


class InvalidToken(Exception):
    pass


def issue_token(user_id: int, secret: str, ttl_minutes: int) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=ttl_minutes)}
    return jwt.encode(payload, secret, algorithm=_ALGORITHM), ttl_minutes * 60


def decode_token(token: str, secret: str) -> int:
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM], options={"require": ["exp", "sub"]})
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise InvalidToken(str(exc)) from exc
