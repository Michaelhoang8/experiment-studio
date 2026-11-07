import math
from .validation import ValidationError

def number(value, name, low, high):
    if isinstance(value, bool):
        raise ValidationError(f'{name} must be numeric')
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        raise ValidationError(f'{name} must be numeric') from None
    if not math.isfinite(result) or not low <= result <= high:
        raise ValidationError(f'{name} must be finite and between {low} and {high}')
    return result
