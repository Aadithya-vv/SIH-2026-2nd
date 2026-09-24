from math import ceil
from app.domain.models import Check, Feasibility, Port, ShipmentRequirement, VesselClass


def check_vessel(shipment: ShipmentRequirement, vessel: VesselClass, ports: list[Port]) -> Feasibility:
    checks = []
    for port in ports:
        for label, required, available in [
            ('DRAFT', vessel.typical_draft, port.maximum_draft),
            ('LOA', vessel.typical_loa, port.maximum_loa),
            ('BEAM', vessel.typical_beam, port.maximum_beam),
        ]:
            margin = round(available - required, 6)
            checks.append(Check(constraint=label, location=port.name,
                status='PASS' if margin >= 0 else 'FAIL', required=required,
                available=available, margin=margin, unit='m',
                explanation=f'{label}: vessel {required:g} m; demo limit {available:g} m; margin {margin:+g} m.'))
        capable = shipment.cargo_type in port.cargo_capabilities
        checks.append(Check(constraint='CARGO_TYPE', location=port.name,
            status='PASS' if capable else 'FAIL', required=1, available=int(capable),
            margin=int(capable)-1, unit='supported', explanation=f'{shipment.cargo_type}: ' + ('supported' if capable else 'not supported')))
    count = ceil(shipment.cargo_quantity_tonnes / vessel.usable_cargo_capacity)
    checks.append(Check(constraint='CAPACITY', location='Shipment',
        status='PASS' if count == 1 else 'CONDITIONAL', required=shipment.cargo_quantity_tonnes,
        available=vessel.usable_cargo_capacity, margin=vessel.usable_cargo_capacity-shipment.cargo_quantity_tonnes,
        unit='tonnes', explanation=f'{count} voyage(s) required; sequential return passages included.'))
    status = 'FAIL' if any(c.status == 'FAIL' for c in checks) else ('CONDITIONAL' if count > 1 else 'PASS')
    return Feasibility(status=status, voyage_count=count, checks=checks)
