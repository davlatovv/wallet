import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

BOT_TOKEN = "123456:TEST-TOKEN"


def make_init_data(user_id: int = 42, *, auth_date: int | None = None,
                   bot_token: str = BOT_TOKEN, tamper: bool = False) -> str:
    fields = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAH",
        "user": json.dumps({"id": user_id, "first_name": "Ann", "username": "ann"}),
    }
    dcs = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    if tamper:
        fields["user"] = json.dumps({"id": 1, "first_name": "Eve"})
    return urlencode(fields)
