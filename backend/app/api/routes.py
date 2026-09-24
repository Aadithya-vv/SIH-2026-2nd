from datetime import datetime, timezone
from pathlib import Path
from app.persistence.sqlite import AnalysisRepository
from fastapi import APIRouter, HTTPException
from app.audit.service import analyze
from app.data.reference import DemoReferenceProvider
from app.domain.models import Analysis, ShipmentRequirement

router = APIRouter()
provider = DemoReferenceProvider()
repository = AnalysisRepository(Path(__file__).resolve().parents[3] / "data" / "analyses.sqlite3")


@router.get('/health')
def health():
    return {'status': 'ok', 'data_mode': 'DEMO_REFERENCE'}


@router.get('/api/reference/ports')
def ports():
    return provider.ports


@router.get('/api/reference/vessels')
def vessels():
    return provider.vessels


def run(shipment):
    try:
        return analyze(shipment, provider, datetime.now(timezone.utc).date())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post('/api/shipments/analyze', response_model=Analysis)
@router.post('/api/optimizer/vessel', response_model=Analysis)
def full_analysis(shipment: ShipmentRequirement):
    result = run(shipment)
    repository.save(result)
    return result


@router.post('/api/feasibility/check')
def feasibility(shipment: ShipmentRequirement):
    return [{'vessel': o.vessel.name, 'feasibility': o.feasibility} for o in run(shipment).options]


@router.post('/api/voyage/estimate')
def voyage(shipment: ShipmentRequirement):
    return [{'vessel': o.vessel.name, 'voyage': o.voyage} for o in run(shipment).options]


@router.post('/api/cost/estimate')
def cost(shipment: ShipmentRequirement):
    return [{'vessel': o.vessel.name, 'cost': o.cost} for o in run(shipment).options]
