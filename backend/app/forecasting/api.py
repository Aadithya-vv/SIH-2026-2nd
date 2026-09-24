import os
from pathlib import Path
from functools import lru_cache
from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from app.market.api import get_store,call
from .models import ForecastTarget
from .service import FreightForecastService
from .artifacts import ArtifactRepository

router=APIRouter()

@lru_cache
def get_artifacts():
    return ArtifactRepository(Path(os.environ.get('FIP_ARTIFACT_DIR',str(Path(__file__).resolve().parents[3]/'artifacts'/'freight'))))

def get_service(store=Depends(get_store),artifacts=Depends(get_artifacts)):
    return FreightForecastService(store,artifacts)

@router.post('/api/forecast/train')
def train(request:ForecastTarget,service=Depends(get_service)):
    return call(lambda:service.train(request))

@router.get('/api/forecast/models')
def models(artifacts=Depends(get_artifacts)):
    return artifacts.list()

@router.get('/api/forecast/models/{model_id}')
def model(model_id:str,artifacts=Depends(get_artifacts)):
    return call(lambda:artifacts.get(model_id))

class BacktestRequest(BaseModel):
    model_id:str=Field(pattern='^[a-f0-9]{24}$')

@router.post('/api/forecast/backtest')
def backtest(request:BacktestRequest,artifacts=Depends(get_artifacts)):
    return call(lambda:artifacts.backtest(request.model_id))

@router.get('/api/forecast/evaluation')
def evaluation(model_id:str,artifacts=Depends(get_artifacts)):
    return call(lambda:{key:artifacts.get(model_id)[key] for key in ['model_id','evaluation_label','periods','leaderboard','selected_models','selection_reason']})

@router.get('/api/forecast/freight')
@router.get('/api/forecast/freight/{series_id}')
def freight(series_id:str,as_of_time:datetime|None=None,service=Depends(get_service)):
    if as_of_time and as_of_time.tzinfo is None: raise HTTPException(422,'as_of_time needs a timezone.')
    return call(lambda:service.forecast(series_id,as_of_time))
