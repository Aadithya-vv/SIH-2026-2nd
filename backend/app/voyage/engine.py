from datetime import date, timedelta
from math import ceil
from app.core.assumptions import ASSUMPTIONS as A, DERIVED
from app.domain.models import Port, ShipmentRequirement, VesselClass, VoyageEstimate


def estimate_voyage(shipment: ShipmentRequirement, vessel: VesselClass, ports: list[Port],
                    distance_nm: float, voyage_count: int, as_of: date) -> VoyageEstimate:
    sea = distance_nm / (vessel.reference_speed * 24) * voyage_count
    returns = distance_nm / (vessel.reference_speed * 24) * (voyage_count - 1)
    loading = shipment.cargo_quantity_tonnes / A['loading_tonnes_per_day']
    unloading = shipment.cargo_quantity_tonnes / A['unloading_tonnes_per_day']
    delay = sum(p.reference_waiting_days for p in ports) * voyage_count
    total = sea + returns + loading + unloading + delay
    arrival = as_of + timedelta(days=ceil(total))
    return VoyageEstimate(distance_nm=distance_nm, sea_days=sea, return_sea_days=returns,
        loading_days=loading, unloading_days=unloading, port_days=loading+unloading,
        expected_delay_days=delay, estimated_total_days=total, estimated_arrival=arrival,
        arrival_feasible=arrival <= shipment.required_arrival_date, provenance=DERIVED)
