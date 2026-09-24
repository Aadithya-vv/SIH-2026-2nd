import json
from pathlib import Path
from typing import Protocol
from app.domain.models import Port, VesselClass

DATA_PATH = Path(__file__).resolve().parents[3] / 'data' / 'demo' / 'reference.json'


class ReferenceProvider(Protocol):
    ports: list[Port]
    vessels: list[VesselClass]
    def distance(self, origin: str, destination: str) -> float: ...


class DemoReferenceProvider:
    def __init__(self):
        data = json.loads(DATA_PATH.read_text())
        self.ports = [Port(**p) for p in data['ports']]
        self.vessels = [VesselClass(**v) for v in data['vessels']]
        self.routes = data['routes']

    def distance(self, origin: str, destination: str) -> float:
        for route in self.routes:
            if route['origin'] == origin and route['destination'] == destination:
                return route['distance_nm']
        raise ValueError('No demo maritime route is available for this port pair.')
