import time

import pytest

from app.presentation.api.auth.telegram import InvalidInitData, validate_init_data
from app.presentation.api.auth.tokens import InvalidToken, decode_token, issue_token
from tests.api.helpers import BOT_TOKEN, make_init_data


def test_valid_init_data():
    user = validate_init_data(make_init_data(7), BOT_TOKEN, 3600)
    assert (user.id, user.username, user.first_name) == (7, "ann", "Ann")


def test_tampered_payload_rejected():
    with pytest.raises(InvalidInitData, match="signature"):
        validate_init_data(make_init_data(7, tamper=True), BOT_TOKEN, 3600)


def test_wrong_bot_token_rejected():
    with pytest.raises(InvalidInitData):
        validate_init_data(make_init_data(7, bot_token="1:OTHER"), BOT_TOKEN, 3600)


def test_expired_rejected():
    old = int(time.time()) - 7200
    with pytest.raises(InvalidInitData, match="expired"):
        validate_init_data(make_init_data(7, auth_date=old), BOT_TOKEN, 3600)


def test_missing_hash_rejected():
    with pytest.raises(InvalidInitData, match="hash"):
        validate_init_data("auth_date=1&user=%7B%7D", BOT_TOKEN, 3600)


SECRET = "s" * 40


def test_token_roundtrip():
    token, ttl = issue_token(99, SECRET, 5)
    assert ttl == 300
    assert decode_token(token, SECRET) == 99


def test_token_wrong_secret_or_garbage_rejected():
    token, _ = issue_token(99, SECRET, 5)
    with pytest.raises(InvalidToken):
        decode_token(token, "x" * 40)
    with pytest.raises(InvalidToken):
        decode_token("nonsense", SECRET)


def test_expired_token_rejected():
    token, _ = issue_token(99, SECRET, -1)
    with pytest.raises(InvalidToken):
        decode_token(token, SECRET)
