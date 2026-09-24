import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from .models import Source, Series, Observation
from .adapters import DemoFreightAdapter, DemoCommodityAdapter, DemoBunkerAdapter, DemoPortCongestionAdapter
from .quality import report

TABLES = {'FREIGHT':'freight_observations','COMMODITY':'commodity_observations',
          'BUNKER':'bunker_observations','PORT':'port_observations'}
SERIES_FIELDS = ['series_id','name','category','source_id','unit','currency','frequency_days',
                 'route','vessel_class','commodity','benchmark','origin_region','fuel_type','port']
SOURCE_FIELDS = ['source_id','name','category','provider','access_type','update_frequency',
                 'license_notes','availability_status','notes']


class MarketStore:
    def __init__(self, path: Path, seed_demo=True):
        self.path=path
        path.parent.mkdir(parents=True,exist_ok=True)
        self.initialize()
        self.seed_registry()
        if seed_demo:
            self.seed_demo()

    @contextmanager
    def connection(self):
        db=sqlite3.connect(self.path,timeout=20)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def initialize(self):
        with self.connection() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS market_schema_versions(version INTEGER PRIMARY KEY);
            INSERT OR IGNORE INTO market_schema_versions VALUES (1);
            CREATE TABLE IF NOT EXISTS data_sources(
              source_id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, provider TEXT NOT NULL,
              access_type TEXT NOT NULL, update_frequency TEXT NOT NULL, expected_units TEXT NOT NULL,
              license_notes TEXT NOT NULL, availability_status TEXT NOT NULL,
              last_successful_ingestion TEXT, notes TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS data_series(
              series_id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
              source_id TEXT NOT NULL REFERENCES data_sources(source_id), unit TEXT NOT NULL, currency TEXT,
              frequency_days INTEGER NOT NULL, route TEXT, vessel_class TEXT, commodity TEXT,
              benchmark TEXT, origin_region TEXT, fuel_type TEXT, port TEXT, provenance TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS series_route ON data_series(route);
            CREATE INDEX IF NOT EXISTS series_port ON data_series(port);
            CREATE TABLE IF NOT EXISTS data_imports(
              import_id TEXT PRIMARY KEY, series_id TEXT NOT NULL REFERENCES data_series(series_id),
              source_id TEXT NOT NULL REFERENCES data_sources(source_id), ingested_at TEXT NOT NULL,
              content_sha256 TEXT NOT NULL UNIQUE, raw_csv TEXT NOT NULL, mapping TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS data_import_rows(
              import_id TEXT NOT NULL REFERENCES data_imports(import_id), row_number INTEGER NOT NULL,
              accepted INTEGER NOT NULL, issues TEXT NOT NULL, raw_values TEXT NOT NULL,
              PRIMARY KEY(import_id,row_number));
            CREATE TABLE IF NOT EXISTS data_quality_reports(
              series_id TEXT PRIMARY KEY REFERENCES data_series(series_id), evaluated_at TEXT NOT NULL,
              report TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS weather_observations(
              id INTEGER PRIMARY KEY, source_id TEXT REFERENCES data_sources(source_id), timestamp TEXT NOT NULL,
              available_at TEXT NOT NULL, port TEXT, route TEXT, wind_knots REAL, wave_height_metres REAL,
              cyclone_flag INTEGER, severity TEXT, route_disruption TEXT, provenance TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS weather_port_time ON weather_observations(port,timestamp);
            CREATE INDEX IF NOT EXISTS weather_route_time ON weather_observations(route,timestamp);
            """)
            for table in TABLES.values():
                db.executescript(f"""
                CREATE TABLE IF NOT EXISTS {table}(
                  id INTEGER PRIMARY KEY, series_id TEXT NOT NULL REFERENCES data_series(series_id),
                  timestamp TEXT NOT NULL, available_at TEXT NOT NULL, value REAL NOT NULL CHECK(value>=0),
                  original_value REAL NOT NULL, original_unit TEXT NOT NULL, original_currency TEXT,
                  quality_flags TEXT NOT NULL, vessels_waiting INTEGER, berth_delay REAL, congestion_level TEXT);
                CREATE INDEX IF NOT EXISTS {table}_series_time ON {table}(series_id,timestamp,available_at);
                CREATE INDEX IF NOT EXISTS {table}_time ON {table}(timestamp);
                """)

    def _source(self, db, source, ingested_at=None):
        existing=db.execute('SELECT expected_units FROM data_sources WHERE source_id=?',(source.source_id,)).fetchone()
        expected=sorted(set(source.expected_units) | set(json.loads(existing['expected_units']) if existing else []))
        values=[getattr(source,f) for f in SOURCE_FIELDS]
        db.execute(f'INSERT INTO data_sources ({",".join(SOURCE_FIELDS)},expected_units,last_successful_ingestion) VALUES ({",".join("?" for _ in range(len(values)+2))}) ON CONFLICT(source_id) DO UPDATE SET expected_units=excluded.expected_units,last_successful_ingestion=COALESCE(excluded.last_successful_ingestion,data_sources.last_successful_ingestion)',
                   values+[json.dumps(expected),ingested_at])

    def _series(self,db,series,observations,quality,as_of):
        values=[getattr(series,f) for f in SERIES_FIELDS]
        db.execute(f'INSERT INTO data_series ({",".join(SERIES_FIELDS)},provenance) VALUES ({",".join("?" for _ in range(len(values)+1))})',values+[series.provenance.model_dump_json()])
        fields=['timestamp','available_at','value','original_value','original_unit','original_currency','quality_flags','vessels_waiting','berth_delay','congestion_level']
        rows=[]
        for observation in observations:
            data=observation.model_dump(mode='json')
            data['quality_flags']=json.dumps(data['quality_flags'])
            # ISO +00:00 consistently sorts lexicographically in SQLite.
            data['timestamp']=observation.timestamp.isoformat()
            data['available_at']=observation.available_at.isoformat()
            rows.append([series.series_id]+[data[f] for f in fields])
        table=TABLES[series.category]
        db.executemany(f'INSERT INTO {table} (series_id,{",".join(fields)}) VALUES ({",".join("?" for _ in range(len(fields)+1))})',rows)
        db.execute('INSERT INTO data_quality_reports VALUES (?,?,?)',(series.series_id,as_of.isoformat(),json.dumps(quality)))

    def seed_registry(self):
        with self.connection() as db:
            for category,name,provider,access,units in [
                ('FREIGHT','Baltic dry bulk indices / BDI, BCI, BPI, BSI','Baltic Exchange','COMMERCIAL_REQUIRED',['index_points','day']),
                ('COMMODITY','Licensed coal / iron ore benchmarks','Provider to be contracted','COMMERCIAL_REQUIRED',['tonne']),
                ('BUNKER','Bunker hub quotations','Provider to be configured','USER_IMPORT',['tonne']),
                ('PORT','Official port waiting / berth observations','Port or terminal authority','USER_IMPORT',['day']),
                ('WEATHER','Weather and route disruptions','Provider to be configured','PUBLIC_API',['knots','metres'])]:
                source=Source(source_id='unavailable-'+category.lower(),name=name,category=category,provider=provider,
                    access_type=access,expected_units=units,availability_status='COMMERCIAL_FEED_REQUIRED' if access=='COMMERCIAL_REQUIRED' else 'SOURCE_NOT_CONNECTED',
                    update_frequency='NOT_CONFIGURED',license_notes='No entitlement or connected dataset. Verify provider terms before integration.',
                    notes='Registry placeholder only; no fetching, scraping, credentials or observations.')
                self._source(db,source)

    def seed_demo(self):
        now=datetime.now(timezone.utc)
        with self.connection() as db:
            for adapter in [DemoFreightAdapter(),DemoCommodityAdapter(),DemoBunkerAdapter(),DemoPortCongestionAdapter()]:
                self._source(db,adapter.get_metadata())
                added=False
                for series,observations in adapter.fetch():
                    if db.execute('SELECT 1 FROM data_series WHERE series_id=?',(series.series_id,)).fetchone():
                        continue
                    rows=[{'accepted':True,'issues':[]} for _ in observations]
                    self._series(db,series,observations,report(rows,observations,series.frequency_days,now),now)
                    added=True
                if added:
                    self._source(db,adapter.get_metadata(),now.isoformat())

    def sources(self):
        with self.connection() as db:
            rows=db.execute('SELECT * FROM data_sources ORDER BY category,name').fetchall()
        result=[]
        for row in rows:
            data=dict(row);data['expected_units']=json.loads(data['expected_units'])
            result.append(Source(**data))
        return result

    def source(self,source_id):
        return next((s for s in self.sources() if s.source_id==source_id),None)

    def series(self,series_id=None):
        with self.connection() as db:
            rows=db.execute('SELECT * FROM data_series'+(' WHERE series_id=?' if series_id else '')+' ORDER BY name',
                            (series_id,) if series_id else ()).fetchall()
        result=[]
        for row in rows:
            data=dict(row);data['provenance']=json.loads(data['provenance']);result.append(Series(**data))
        if series_id:
            if not result: raise KeyError('Unknown series ID.')
            return result[0]
        return result

    def observations(self,series_id,start=None,end=None,cutoff=None):
        series=self.series(series_id)
        table=TABLES[series.category]
        query=f'SELECT * FROM {table} WHERE series_id=?'
        params=[series_id]
        for condition,value in [('timestamp>=?',start),('timestamp<=?',end),('available_at<=?',cutoff)]:
            if value is not None:
                query+=' AND '+condition;params.append(value.isoformat())
        query+=' ORDER BY timestamp,available_at,id'
        with self.connection() as db:
            rows=db.execute(query,params).fetchall()
        result=[]
        for row in rows:
            data=dict(row);data.pop('id');data.pop('series_id');data['quality_flags']=json.loads(data['quality_flags'])
            result.append(Observation(**data))
        return result

    def quality(self,series_id,as_of):
        series=self.series(series_id)
        with self.connection() as db:
            row=db.execute('SELECT report FROM data_quality_reports WHERE series_id=?',(series_id,)).fetchone()
        result=json.loads(row['report'])
        end=datetime.fromisoformat(result['end']) if result['end'] else None
        result['latest_age_days']=round((as_of-end).total_seconds()/86400,2) if end else None
        result['stale']=bool(end and (as_of-end).total_seconds()/86400>max(7,series.frequency_days*2))
        result['warnings']=[w for w in result['warnings'] if w!='STALE_DATA']+(['STALE_DATA'] if result['stale'] else [])
        result['status']='UNUSABLE' if not result['rows_accepted'] else 'USABLE_WITH_WARNINGS' if result['warnings'] else 'USABLE'
        return result

    def ingest(self,adapter,source,series,observations,rows,quality,now):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            existing=db.execute('SELECT series_id FROM data_imports WHERE content_sha256=?',(adapter.fingerprint,)).fetchone()
            if existing:
                return existing['series_id'],True
            self._source(db,source,now.isoformat())
            self._series(db,series,observations,quality,now)
            request=adapter.request
            db.execute('INSERT INTO data_imports VALUES (?,?,?,?,?,?,?)',
                (adapter.fingerprint,series.series_id,source.source_id,now.isoformat(),adapter.fingerprint,
                 request.csv_text,request.model_dump_json(exclude={'csv_text','commit','preview_hash'})))
            db.executemany('INSERT INTO data_import_rows VALUES (?,?,?,?,?)',
                [(adapter.fingerprint,row['row_number'],int(row['accepted']),json.dumps(row['issues']),json.dumps(row['raw'])) for row in rows])
        return series.series_id,False
