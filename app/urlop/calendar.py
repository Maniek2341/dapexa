from datetime import timedelta
from decimal import Decimal

import holidays


def calculate_working_days(date_from, date_to):
    if not date_from or not date_to or date_from > date_to:
        return Decimal("0")
    if (date_to - date_from).days > 366:
        raise ValueError("Zakres urlopu jest za długi.")

    public_holidays = holidays.country_holidays("PL", years=range(date_from.year, date_to.year + 1))
    current = date_from
    total = 0
    while current <= date_to:
        if current.weekday() < 5 and current not in public_holidays:
            total += 1
        current += timedelta(days=1)
    return Decimal(total)
