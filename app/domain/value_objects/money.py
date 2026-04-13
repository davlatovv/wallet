from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "UZS"

    def __post_init__(self) -> None:
        if self.amount < Decimal("0"):
            raise ValueError(f"Money amount cannot be negative: {self.amount}")

    def __add__(self, other: "Money") -> "Money":
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        result = self.amount - other.amount
        return Money(result, self.currency)

    def __mul__(self, factor: Decimal) -> "Money":
        return Money((self.amount * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def __lt__(self, other: "Money") -> bool:
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        return self.amount > other.amount

    def ratio(self, other: "Money") -> Decimal:
        if other.amount == Decimal("0"):
            return Decimal("0")
        return self.amount / other.amount

    def format(self) -> str:
        return f"{self.amount:,.2f} {self.currency}"
