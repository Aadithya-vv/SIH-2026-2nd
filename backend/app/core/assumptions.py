from datetime import date
from app.domain.models import ProvenanceMetadata, SourceType

REFERENCE_DATE = date(2026, 9, 1)
ASSUMPTIONS = {
    'currency': 'USD',
    'fuel_usd_per_tonne': 600.0,
    'loading_tonnes_per_day': 25000.0,
    'unloading_tonnes_per_day': 20000.0,
    'free_waiting_days_per_voyage': 1.0,
    'demurrage_fraction_of_daily_hire': 0.8,
    'lighterage_usd': 0.0,
    'storage_usd': 0.0,
    'execution': 'Sequential voyages by one vessel; return passage between deliveries; immediate availability at origin.',
}


def provenance(kind: SourceType, name: str, notes: str, effective_date=REFERENCE_DATE):
    return ProvenanceMetadata(source_type=kind, source_name=name,
                              effective_date=effective_date, notes=notes)


DEMO = provenance(SourceType.ASSUMED, 'DEMO_REFERENCE v1',
                  'Illustrative values, not official port limits or market quotations. USD; m; tonnes; knots; days.')
DERIVED = provenance(SourceType.DERIVED, 'Batch 1 deterministic engine',
                     'Derived from shipment, DEMO_REFERENCE and centralized assumptions; not a validated operational estimate.')
