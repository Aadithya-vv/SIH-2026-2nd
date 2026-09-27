import os
from datetime import timedelta
from pathlib import Path
from functools import lru_cache
from fastapi import APIRouter, Depends
from app.api.routes import provider
from app.market.api import get_store, call
from app.forecasting.api import get_service as get_forecasts
from .models import CharterTimingRequest, CharterTimingDecision
from .repository import CharterRepository
from .service import CharterTimingService
from . import demos

router = APIRouter(prefix='/api/charter',tags=['Charter timing'])


@lru_cache
def get_repository():
    return CharterRepository(Path(os.environ.get('FIP_ANALYSIS_DB',str(Path(__file__).resolve().parents[3]/'data'/'analyses.sqlite3'))))


def get_service(store=Depends(get_store),forecasts=Depends(get_forecasts),repository=Depends(get_repository)):
    return CharterTimingService(provider,store,forecasts,repository)


@router.post('/analyze',response_model=CharterTimingDecision)
def analyze(request:CharterTimingRequest,service=Depends(get_service)):
    return call(lambda:service.analyze(request))


@router.get('/history')
def history(repository=Depends(get_repository)):
    return repository.history()


def resolved_presets(forecasts,service):
    presets = demos.presets(forecasts)
    # Calculate B deadline using identical reference + market timing semantics; no price-based fixed label.
    # Use a non-persisting repository so loading presets never creates audit analyses.
    class NoSave:
        def save(self, decision): pass
    calculator = CharterTimingService(service.provider,service.store,service.forecasts,NoSave())
    basis = calculator.analyze(CharterTimingRequest(**presets[0]['request']))
    days = basis.voyage_context['rounded_buffered_duration_days']
    presets[1]['request']['shipment']['required_arrival_date'] = (demos.AS_OF.date()+timedelta(days=days)).isoformat()
    return presets


@router.get('/demos')
def demo_presets(forecasts=Depends(get_forecasts),service=Depends(get_service)):
    return resolved_presets(forecasts,service)


@router.post('/demos/prepare')
def prepare_demos(forecasts=Depends(get_forecasts),service=Depends(get_service)):
    demos.prepare(service.store,forecasts)
    return resolved_presets(forecasts,service)


@router.get('/{analysis_id}/explanation')
def explanation(analysis_id:str,repository=Depends(get_repository)):
    return call(lambda:{'analysis_id':analysis_id,'explanation':repository.get(analysis_id).explanation,
        'policy':repository.get(analysis_id).policy})


@router.get('/{analysis_id}',response_model=CharterTimingDecision)
def saved(analysis_id:str,repository=Depends(get_repository)):
    return call(lambda:repository.get(analysis_id))
