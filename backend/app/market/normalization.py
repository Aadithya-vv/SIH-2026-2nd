from datetime import datetime, timezone
import math

# Currency is retained separately. No FX conversions are performed.
UNITS = {'tonne': ('tonne', 1.0), 't': ('tonne', 1.0), 'metric_ton': ('tonne', 1.0),
         'kg': ('tonne', 1000.0), 'day': ('day', 1.0), 'days': ('day', 1.0),
         'hour': ('day', 1/24), 'hours': ('day', 1/24), 'index_points': ('index_points', 1.0),
         'points': ('index_points', 1.0)}


def unit_rule(category, unit, currency):
    if unit not in UNITS:
        raise ValueError('Unsupported unit. Use tonne, t, metric_ton, kg, day, days, hour, hours or index_points.')
    canonical, factor = UNITS[unit]
    allowed = {'FREIGHT': {'tonne','day','index_points'}, 'COMMODITY': {'tonne'},
               'BUNKER': {'tonne'}, 'PORT': {'day'}}
    if canonical not in allowed.get(category,set()):
        raise ValueError('Unit is incompatible with the selected category.')
    priced = category != 'PORT' and canonical != 'index_points'
    if priced and (not currency or len(currency)!=3 or not currency.isalpha() or currency!=currency.upper()):
        raise ValueError('A three-letter uppercase currency is required for prices.')
    if not priced and currency:
        raise ValueError('Index points and waiting days must not have a currency.')
    if priced and unit in ('hour','hours'):
        factor = 24.0  # price/hour -> price/day; waiting hours instead divide by 24
    return canonical, factor


def parse_time(raw):
    value = datetime.fromisoformat(str(raw).strip().replace('Z','+00:00'))
    # ISO date-only and naive timestamps explicitly mean UTC under the import contract.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def numeric(raw):
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError('Non-finite numeric input.')
    return value
