from decimal import Decimal, ROUND_HALF_UP
from app.core.assumptions import ASSUMPTIONS as A, DERIVED
from app.domain.models import CostBreakdown, Port, VesselClass, VoyageEstimate


def rounded(value):
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def estimate_cost(vessel: VesselClass, ports: list[Port], voyage: VoyageEstimate,
                  count: int, quantity: float) -> CostBreakdown:
    # Hire excludes excess waiting charged as demurrage: no double-counting.
    excess_wait = max(0, voyage.expected_delay_days - A['free_waiting_days_per_voyage'] * count)
    components = dict(
        ocean_freight=rounded((voyage.estimated_total_days-excess_wait)*vessel.reference_daily_charter_rate),
        bunker_component=rounded((voyage.sea_days+voyage.return_sea_days)*vessel.fuel_tonnes_per_sea_day*A['fuel_usd_per_tonne']),
        port_cost=rounded(sum(p.reference_port_cost for p in ports)*count),
        expected_demurrage=rounded(excess_wait*vessel.reference_daily_charter_rate*A['demurrage_fraction_of_daily_hire']),
        lighterage_if_applicable=A['lighterage_usd'], storage_if_applicable=A['storage_usd'])
    total = sum(Decimal(str(value)) for value in components.values())
    return CostBreakdown(**components, total_logistics_cost=float(total),
        cost_per_tonne=rounded(total/Decimal(str(quantity))), provenance=DERIVED)
