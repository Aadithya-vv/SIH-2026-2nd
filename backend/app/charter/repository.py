import json
import sqlite3
from .models import CharterTimingDecision


class CharterRepository:
    """Additive table alongside existing Phase 1 analysis snapshots."""
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS charter_analyses (id TEXT PRIMARY KEY, generated_at TEXT NOT NULL, payload TEXT NOT NULL)')

    def save(self, decision):
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT OR IGNORE INTO charter_analyses VALUES (?,?,?)',
                (decision.analysis_id,decision.generated_at,decision.model_dump_json()))

    def get(self, analysis_id):
        with sqlite3.connect(self.path) as db:
            row = db.execute('SELECT payload FROM charter_analyses WHERE id=?',(analysis_id,)).fetchone()
        if row is None: raise KeyError('Charter analysis not found.')
        return CharterTimingDecision.model_validate_json(row[0])

    def history(self):
        with sqlite3.connect(self.path) as db:
            rows = db.execute('SELECT payload FROM charter_analyses ORDER BY generated_at DESC LIMIT 100').fetchall()
        result = []
        for row in rows:
            d = json.loads(row[0])
            result.append({k:d[k] for k in ['analysis_id','generated_at','request','recommendation',
                'recommended_window_start','recommended_window_end','median_saving','evidence_status']})
        return result
