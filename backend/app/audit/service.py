from datetime import date
from app.core.assumptions import ASSUMPTIONS, DEMO, DERIVED, provenance
from app.data.reference import ReferenceProvider
from app.domain.models import Analysis, ShipmentRequirement, SourceType, VesselOption
from app.feasibility.engine import check_vessel
from app.voyage.engine import estimate_voyage
from app.costing.engine import estimate_cost
from app.optimization.vessel import recommend


def analyze(shipment: ShipmentRequirement, provider: ReferenceProvider, as_of: date) -> Analysis:
    if shipment.required_arrival_date < as_of:
        raise ValueError('Required arrival date cannot be before the analysis date.')
    ports = []
    for name, country in [(shipment.origin_port, shipment.origin_country),
                          (shipment.destination_port, shipment.destination_country)]:
        port = next((p for p in provider.ports if p.name == name and p.country == country), None)
        if port is None:
            raise ValueError(f'Unknown port/country combination: {name}, {country}.')
        ports.append(port)
    distance = provider.distance(shipment.origin_port, shipment.destination_port)
    options = []
    for vessel in provider.vessels:
        feasibility = check_vessel(shipment, vessel, ports)
        voyage = estimate_voyage(shipment, vessel, ports, distance, feasibility.voyage_count, as_of)
        cost = estimate_cost(vessel, ports, voyage, feasibility.voyage_count, shipment.cargo_quantity_tonnes)
        options.append(VesselOption(vessel=vessel, feasibility=feasibility, voyage=voyage, cost=cost))
    return Analysis(analysis_date=as_of, shipment=shipment, reference_ports=ports, options=options,
        recommendation=recommend(options), assumptions=ASSUMPTIONS,
        provenance={'shipment': provenance(SourceType.USER_INPUT, 'Shipment submission', 'All shipment fields as submitted; optional inventory and cargo value are not used in Batch 1.', as_of),
            'ports': DEMO, 'vessels': DEMO, 'route_distance_nm': DEMO,
            'assumptions': DEMO, 'feasibility': DERIVED, 'recommendation': DERIVED,
            'analysis_date': provenance(SourceType.DERIVED, 'Server UTC clock', 'Start of analysis day; immediate departure assumption.', as_of)})
