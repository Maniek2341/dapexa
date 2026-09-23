from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django import template

register = template.Library()


@register.filter
def decimal_hours_to_hm(value):
    if value in (None, ""):
        return "0:00"

    try:
        value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value

    total_minutes = int((value * 60).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    hours = total_minutes // 60
    minutes = total_minutes % 60

    return f"{hours}:{minutes:02d}"

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)