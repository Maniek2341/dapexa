# app/obsluga/services/periods.py

import calendar
from datetime import date, timedelta


def get_contract_current_period(contract, today=None):
    today = today or date.today()

    if contract.frequency == "weekly":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)

    elif contract.frequency == "monthly":
        start = today.replace(day=1)
        end = today.replace(
            day=calendar.monthrange(today.year, today.month)[1]
        )

    elif contract.frequency == "quarterly":
        start_month = ((today.month - 1) // 3) * 3 + 1
        end_month = start_month + 2

        start = date(today.year, start_month, 1)
        end = date(
            today.year,
            end_month,
            calendar.monthrange(today.year, end_month)[1]
        )

    elif contract.frequency == "half_yearly":
        if today.month <= 6:
            start = date(today.year, 1, 1)
            end = date(today.year, 6, 30)
        else:
            start = date(today.year, 7, 1)
            end = date(today.year, 12, 31)

    elif contract.frequency == "yearly":
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)

    else:
        start = today
        end = today

    return start, end