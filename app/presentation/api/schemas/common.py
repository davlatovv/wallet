from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, PlainSerializer

_CENTS = Decimal("0.01")

# Money is always a decimal string with exactly 2 decimals on the wire, never a float.
# Uniform formatting matters: a freshly created row and one re-read from Numeric(15,2)
# must serialize identically.
MoneyStr = Annotated[
    Decimal, PlainSerializer(lambda v: format(v.quantize(_CENTS), "f"), return_type=str)
]


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: object | None = None

# Percentages (interest rates) use the same fixed 2-decimal wire format.
RateStr = MoneyStr
