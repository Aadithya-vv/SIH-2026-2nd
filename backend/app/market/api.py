from datetime import date, datetime, time, timezone
from functools import lru_cache
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from .models import ImportRequest, FeatureRequest
from .store import MarketStore
from .service import MarketDataService, MarketSnapshotService
from .features import build_features

router=APIRouter()


@lru_cache
def get_store():
    return MarketStore(Path(os.environ.get('FIP_MARKET_DB', str(Path(__file__).resolve().parents[3]/'data'/'market.sqlite3'))))


def now(): return datetime.now(timezone.utc)


def window(start,end):
    if start and end and start>end:
        raise HTTPException(422,'Start date must not follow end date.')
    return (datetime.combine(start,time.min,tzinfo=timezone.utc) if start else None,
            datetime.combine(end,time.max,tzinfo=timezone.utc) if end else None)


def call(action):
    try: return action()
    except KeyError as exc: raise HTTPException(404,str(exc)) from exc
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc


@router.get('/api/data/sources')
def sources(store=Depends(get_store)): return store.sources()


@router.get('/api/data/catalog')
@router.get('/api/data/series')
def catalog(store=Depends(get_store)): return MarketDataService(store).catalog(now())


@router.get('/api/data/series/{series_id}')
def history(series_id:str,start:date|None=None,end:date|None=None,store=Depends(get_store)):
    a,b=window(start,end)
    return call(lambda:{'series':store.series(series_id),'observations':store.observations(series_id,a,b,now())})


@router.get('/api/data/series/{series_id}/quality')
def quality(series_id:str,store=Depends(get_store)):
    return call(lambda:store.quality(series_id,now()))


@router.post('/api/data/import/csv')
def import_csv(request:ImportRequest,store=Depends(get_store)):
    return call(lambda:MarketDataService(store).import_csv(request,now()))


@router.get('/api/market/snapshot')
def snapshot(origin:str,destination:str,vessel_class:str,cargo_type:str,as_of_time:datetime|None=None,origin_region:str|None=None,store=Depends(get_store)):
    as_of=as_of_time or now()
    if as_of.tzinfo is None: raise HTTPException(422,'as_of_time requires a timezone.')
    if as_of>now(): raise HTTPException(422,'as_of_time cannot be in the future.')
    return MarketSnapshotService(store).snapshot(origin,destination,vessel_class,cargo_type,as_of.astimezone(timezone.utc),origin_region)


@router.get('/api/market/trends')
def trends(series_id:str,start:date|None=None,end:date|None=None,store=Depends(get_store)):
    a,b=window(start,end)
    return call(lambda:MarketDataService(store).trends(series_id,a,b,now()))


@router.post('/api/features/build')
def features(request:FeatureRequest,store=Depends(get_store)):
    if request.cutoff_time>now(): raise HTTPException(422,'cutoff_time cannot be in the future.')
    return call(lambda:build_features(store,request))
