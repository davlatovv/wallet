from decimal import Decimal, ROUND_HALF_UP


class CreditCalculator:
    """Calculates credit payment schedules (annuity and differential)."""

    QUANT = Decimal("0.01")

    @staticmethod
    def annuity_payment(principal: Decimal, annual_rate: Decimal, months: int) -> Decimal:
        """
        PMT = P * r*(1+r)^n / ((1+r)^n - 1)
        where r = annual_rate / 12 / 100
        """
        if annual_rate == Decimal("0"):
            return (principal / months).quantize(CreditCalculator.QUANT, rounding=ROUND_HALF_UP)
        r = annual_rate / Decimal("1200")
        factor = (1 + r) ** months
        pmt = principal * r * factor / (factor - 1)
        return pmt.quantize(CreditCalculator.QUANT, rounding=ROUND_HALF_UP)

    @staticmethod
    def differential_payment(
        principal: Decimal,
        annual_rate: Decimal,
        months: int,
        month_num: int,  # 1-based
    ) -> Decimal:
        """
        D_n = P/n + (P - P*(n-1)/n) * r/12
        = P/n + P*(1 - (n-1)/n) * r/12
        """
        r = annual_rate / Decimal("1200")
        principal_part = (principal / months).quantize(CreditCalculator.QUANT, rounding=ROUND_HALF_UP)
        remaining = principal - principal_part * (month_num - 1)
        interest_part = (remaining * r).quantize(CreditCalculator.QUANT, rounding=ROUND_HALF_UP)
        return principal_part + interest_part

    @staticmethod
    def full_schedule(
        principal: Decimal,
        annual_rate: Decimal,
        months: int,
        payment_type: str,  # "annuity" | "differential"
    ) -> list[dict]:
        """
        Returns list of dicts per month:
        {month, payment, principal_part, interest_part, balance}
        """
        schedule = []
        balance = principal
        r = annual_rate / Decimal("1200")

        if payment_type == "annuity":
            pmt = CreditCalculator.annuity_payment(principal, annual_rate, months)
            for m in range(1, months + 1):
                interest_part = (balance * r).quantize(CreditCalculator.QUANT, rounding=ROUND_HALF_UP)
                principal_part = pmt - interest_part
                if m == months:
                    principal_part = balance
                    pmt = principal_part + interest_part
                balance = max(balance - principal_part, Decimal("0"))
                schedule.append({
                    "month": m,
                    "payment": principal_part + interest_part,
                    "principal_part": principal_part,
                    "interest_part": interest_part,
                    "balance": balance,
                })
        else:  # differential
            principal_part = (principal / months).quantize(CreditCalculator.QUANT, rounding=ROUND_HALF_UP)
            for m in range(1, months + 1):
                interest_part = (balance * r).quantize(CreditCalculator.QUANT, rounding=ROUND_HALF_UP)
                if m == months:
                    principal_part = balance
                payment = principal_part + interest_part
                balance = max(balance - principal_part, Decimal("0"))
                schedule.append({
                    "month": m,
                    "payment": payment,
                    "principal_part": principal_part,
                    "interest_part": interest_part,
                    "balance": balance,
                })

        return schedule
