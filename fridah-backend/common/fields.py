from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from rest_framework import serializers

SIX_PLACES = Decimal('0.000001')      # about 0.1 metre, far finer than a building needs


class _Coordinate(serializers.DecimalField):
    """
    A map coordinate as sent by Google Maps: up to ~15 decimals. Round it to the 6 we store instead of rejecting it
    (the plain DecimalField refuses anything over 9 digits, which made saving a pinned address fail), and keep it
    inside the real range so a typo cannot place a house at latitude 500.
    """
    def __init__(self, limit, **kwargs):
        kwargs.setdefault('required', False)
        kwargs.setdefault('allow_null', True)
        super().__init__(max_digits=9, decimal_places=6, min_value=-limit, max_value=limit, **kwargs)

    def to_internal_value(self, data):
        if isinstance(data, (int, float, str)) and str(data).strip() != '':
            try:
                data = str(Decimal(str(data).strip()).quantize(SIX_PLACES, rounding=ROUND_HALF_UP))
            except InvalidOperation:
                pass                                  # not a number: let the normal validation report it
        return super().to_internal_value(data)


class LatitudeField(_Coordinate):
    def __init__(self, **kwargs):
        super().__init__(90, **kwargs)


class LongitudeField(_Coordinate):
    def __init__(self, **kwargs):
        super().__init__(180, **kwargs)
