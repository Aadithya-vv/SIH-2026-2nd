from datetime import datetime, timezone
import numpy as np
from .adapters import CSVImportAdapter
from .quality import STALE_DAYS


def usable_history(observations,as_of):
    # Latest eligible revision per observation time. Flagged duplicate rows never silently win.
    result={}
    for o in observations:
        if o.timestamp<=as_of and o.available_at<=as_of and 'DUPLICATE' not in o.quality_flags:
            if o.timestamp not in result or o.available_at>=result[o.timestamp].available_at:
                result[o.timestamp]=o
    return [result[t] for t in sorted(result)]


class MarketDataService:
    def __init__(self,store): self.store=store

    def import_csv(self,request,now):
        adapter=CSVImportAdapter(request)
        source,series,observations,rows,quality=adapter.validate(adapter.fetch(),now)
        result={'preview_hash':adapter.fingerprint,'series_id':series.series_id,'source_label':source.name,
                'unit':series.unit,'currency':series.currency,'quality':quality,'rows':rows,
                'normalization':{'original_unit':request.unit,'canonical_unit':series.unit,
                    'currency_conversion':'NONE','availability': 'USER_ASSERTED_PUBLICATION' if request.available_at_column else 'INGESTION_TIME'},
                'committed':False,'already_ingested':False}
        if request.commit:
            if request.preview_hash!=adapter.fingerprint:
                raise ValueError('Validate this exact dataset before ingestion; preview hash is missing or differs.')
            if not observations:
                raise ValueError('No valid observations. Nothing was ingested.')
            result['series_id'],result['already_ingested']=self.store.ingest(adapter,source,series,observations,rows,quality,now)
            result['committed']=True
            if result['already_ingested']:
                result['quality']=self.store.quality(result['series_id'],now)
        return result

    def catalog(self,now):
        result=[]
        sources={s.source_id:s for s in self.store.sources()}
        for series in self.store.series():
            observations=self.store.observations(series.series_id,cutoff=now)
            usable=usable_history(observations,now)
            quality=self.store.quality(series.series_id,now)
            result.append({'series':series,'source':sources[series.source_id],'records':len(observations),
                'start':observations[0].timestamp if observations else None,
                'end':observations[-1].timestamp if observations else None,
                'latest':usable[-1].value if usable else None,'quality':quality,
                'status':'DEMO' if series.provenance.source_type=='SIMULATED' else 'IMPORTED',
                'forecast_suitability':'DEMO_ONLY' if series.provenance.source_type=='SIMULATED' else 'REVIEW_REQUIRED' if quality['warnings'] else 'STRUCTURALLY_USABLE_NOT_VERIFIED'})
        return result

    def trends(self,series_id,start,end,as_of):
        values=usable_history(self.store.observations(series_id,start,end,as_of),as_of)
        x=np.array([o.value for o in values],dtype=float)
        change=float(x[-1]-x[-2]) if len(x)>=2 else None
        percent=float(100*(x[-1]/x[-2]-1)) if len(x)>=2 and x[-2]!=0 else None
        returns=np.diff(x[-31:])/x[-31:-1] if len(x)>=31 and np.all(x[-31:-1]>0) else None
        return {'series_id':series_id,'records':len(x),'latest':float(x[-1]) if len(x) else None,
                'mean_7':float(np.mean(x[-7:])) if len(x)>=7 else None,
                'mean_30':float(np.mean(x[-30:])) if len(x)>=30 else None,
                'change':change,'change_percent':percent,
                'rolling_volatility':float(np.std(returns,ddof=1)) if returns is not None else None,
                'minimum':float(np.min(x)) if len(x) else None,'maximum':float(np.max(x)) if len(x) else None,
                'method':'Descriptive only. Means use last 7/30 distinct observation periods; volatility is sample standard deviation of last 30 fractional returns, not annualized. No gap filling.',
                'provenance':'DERIVED','warnings':self.store.quality(series_id,as_of)['warnings']}


class MarketSnapshotService:
    def __init__(self,store): self.store=store

    def snapshot(self,origin,destination,vessel_class,cargo_type,as_of,origin_region=None):
        relevant={
            'freight':lambda s:s.category=='FREIGHT' and s.vessel_class==vessel_class and (not s.route or s.route==origin+' -> '+destination),
            'commodity':lambda s:s.category=='COMMODITY' and s.commodity==cargo_type,
            'bunker':lambda s:s.category=='BUNKER' and s.port=='Singapore' and s.fuel_type=='VLSFO',
            'port':lambda s:s.category=='PORT' and s.port==destination,
        }
        context={}
        series_catalog=self.store.series()
        for key,match in relevant.items():
            candidates=[]
            for series in series_catalog:
                if not match(series): continue
                history=usable_history(self.store.observations(series.series_id,end=as_of,cutoff=as_of),as_of)
                if history:
                    observation=history[-1]
                    age=(as_of-observation.timestamp).total_seconds()/86400
                    stale=age>max(STALE_DAYS,series.frequency_days*2)
                    # Freshness, then non-demo, then exact origin benchmark, then newest observation.
                    rank=(stale,series.provenance.source_type=='SIMULATED',
                          bool(origin_region and series.origin_region!=origin_region),-observation.timestamp.timestamp(),series.series_id)
                    candidates.append((rank,series,observation,age,stale))
            if not candidates:
                context[key]={'available':False,'reason':'No relevant observation known by as_of_time. No replacement value fabricated.'}
                continue
            _,series,o,age,stale=min(candidates,key=lambda c:c[0])
            context[key]={'available':True,'series_id':series.series_id,'series_name':series.name,
                'value':o.value,'timestamp':o.timestamp,'available_at':o.available_at,'unit':series.unit,'currency':series.currency,
                'source':self.store.source(series.source_id),'provenance':series.provenance,
                'freshness':{'age_days':round(age,2),'status':'STALE' if stale else 'WITHIN_THRESHOLD'},
                'quality_flags':o.quality_flags,'context_note':
                'Representative cargo benchmark; not a shipment quotation.' if key=='commodity' else
                'Singapore VLSFO proxy; actual bunkering plan is not modelled.' if key=='bunker' else
                'Vessel-class historical context, not a route freight quote.' if key=='freight' else 'Destination waiting observation.',
                'selection_policy':'Fresh before stale; non-demo before simulated; origin-matched benchmark before proxy; latest known observation. Every fallback remains labelled.'}
        return {'as_of_time':as_of,'origin':origin,'destination':destination,'vessel_class':vessel_class,'cargo_type':cargo_type,
                'context':context,'cost_integration':'CONTEXT_ONLY: Batch 1 costs continue using explicit reference assumptions.'}
