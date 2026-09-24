import sqlite3
from pathlib import Path
from app.domain.models import Analysis


class AnalysisRepository:
    def __init__(self, path: Path):
        self.path = path

    def save(self, analysis: Analysis):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS analyses (id INTEGER PRIMARY KEY, analysis_date TEXT, payload TEXT)')
            db.execute('INSERT INTO analyses (analysis_date, payload) VALUES (?, ?)',
                       (analysis.analysis_date.isoformat(), analysis.model_dump_json()))
