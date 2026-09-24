from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.domain.models import ShipmentRequirement
from app.data.reference import DemoReferenceProvider
from app.audit.service import analyze
from app.feasibility.engine import check_vessel
from app.voyage.engine import estimate_voyage
from app.costing.engine import estimate_cost
from app.optimization.vessel import recommend
from app.persistence.sqlite import AnalysisRepository

DAY = date(2026, 9, 20)

@pytest.fixture(autouse=True)
def isolated_api_storage(tmp_path, monkeypatch):
    monkeypatch.setattr('app.api.routes.repository', AnalysisRepository(tmp_path/'api.sqlite3'))


@pytest.fixture
def provider():
    return DemoReferenceProvider()

@pytest.fixture
def shipment():
    return ShipmentRequirement(cargo_type='COKING_COAL', cargo_quantity_tonnes=70000,
        origin_country='Australia', origin_port='Newcastle', destination_country='India',
        destination_port='Paradip', required_arrival_date=DAY+timedelta(days=120))

def test_port_pass(provider, shipment):
    result = analyze(shipment, provider, DAY)
    assert result.options[2].feasibility.status == 'PASS'

@pytest.mark.parametrize('field,constraint', [('maximum_draft','DRAFT'),('maximum_loa','LOA'),('maximum_beam','BEAM')])
def test_each_constraint(provider, shipment, field, constraint):
    port = provider.ports[3].model_copy(update={field:1})
    result = check_vessel(shipment, provider.vessels[2], [provider.ports[0],port])
    assert result.status == 'FAIL'
    assert any(c.constraint == constraint and c.status == 'FAIL' and c.margin < 0 for c in result.checks)

def test_origin_constraint(provider, shipment):
    port = provider.ports[0].model_copy(update={'maximum_draft':1})
    assert check_vessel(shipment, provider.vessels[2], [port,provider.ports[3]]).status == 'FAIL'

def test_boundary_and_multiple(provider, shipment):
    vessel = provider.vessels[0]
    shipment.cargo_quantity_tonnes = vessel.usable_cargo_capacity
    assert check_vessel(shipment,vessel,[provider.ports[0]]).voyage_count == 1
    shipment.cargo_quantity_tonnes += 1
    result = check_vessel(shipment,vessel,[provider.ports[0]])
    assert result.voyage_count == 2
    assert result.status == 'CONDITIONAL'

def test_dimension_equality(provider, shipment):
    vessel = provider.vessels[2]
    port = provider.ports[0].model_copy(update={'maximum_draft':vessel.typical_draft,'maximum_loa':vessel.typical_loa,'maximum_beam':vessel.typical_beam})
    assert check_vessel(shipment,vessel,[port]).status == 'PASS'

def test_cargo_unsupported(provider, shipment):
    port = provider.ports[0].model_copy(update={'cargo_capabilities':[]})
    assert check_vessel(shipment,provider.vessels[2],[port]).status == 'FAIL'

def test_voyage_formula(provider, shipment):
    v = provider.vessels[0]
    result = estimate_voyage(shipment,v,[provider.ports[0],provider.ports[3]],2880,2,DAY)
    assert result.sea_days == 20
    assert result.return_sea_days == 10
    assert result.port_days == pytest.approx(6.3)
    assert result.expected_delay_days == 6
    assert result.estimated_total_days == pytest.approx(42.3)
    assert result.estimated_arrival == DAY+timedelta(days=43)

def test_cost_sum_and_demurrage(provider, shipment):
    v = provider.vessels[0]
    ports = [provider.ports[0],provider.ports[3]]
    voyage = estimate_voyage(shipment,v,ports,2880,2,DAY)
    cost = estimate_cost(v,ports,voyage,2,70000)
    assert cost.expected_demurrage == 4*11000*0.8
    assert cost.ocean_freight == pytest.approx((42.3-4)*11000)
    assert cost.bunker_component == 30*18*600
    assert cost.port_cost == 340000
    assert cost.total_logistics_cost == pytest.approx(sum([cost.ocean_freight,cost.bunker_component,cost.port_cost,cost.expected_demurrage,cost.lighterage_if_applicable,cost.storage_if_applicable]))
    assert cost.cost_per_tonne == round(cost.total_logistics_cost/70000,2)

def test_no_demurrage_under_allowance(provider, shipment):
    ports = [p.model_copy(update={'reference_waiting_days':0}) for p in provider.ports[:2]]
    voyage = estimate_voyage(shipment,provider.vessels[0],ports,2880,2,DAY)
    assert estimate_cost(provider.vessels[0],ports,voyage,2,70000).expected_demurrage == 0

def test_recommendation_cheapest_and_feasible(provider, shipment):
    result = analyze(shipment,provider,DAY)
    eligible = [o for o in result.options if o.feasibility.status != 'FAIL' and o.voyage.arrival_feasible]
    best = min(eligible,key=lambda o:o.cost.total_logistics_cost)
    assert result.recommendation.recommended_vessel == best.vessel.name
    assert result.recommendation.recommended_vessel != 'CAPESIZE'

def test_arrival_changes_selection(provider, shipment):
    options = analyze(shipment,provider,DAY).options
    cheapest = min([o for o in options if o.feasibility.status != 'FAIL'],key=lambda o:o.cost.total_logistics_cost)
    cheapest.voyage.arrival_feasible = False
    assert recommend(options).recommended_vessel != cheapest.vessel.name
    shipment.required_arrival_date = DAY
    assert analyze(shipment,provider,DAY).recommendation.recommended_vessel is None

def test_provenance_determinism(provider, shipment):
    a = analyze(shipment,provider,DAY)
    assert a == analyze(shipment,provider,DAY)
    output = a.model_dump(mode='json')
    assert output['provenance']['shipment']['source_type'] == 'USER_INPUT'
    assert output['options'][0]['cost']['provenance']['source_type'] == 'DERIVED'
    assert output['options'][0]['vessel']['provenance']['source_type'] == 'ASSUMED'

def test_api_valid(shipment):
    shipment.required_arrival_date = date.today()+timedelta(days=120)
    with TestClient(app) as client:
        response = client.post('/api/shipments/analyze',json=shipment.model_dump(mode='json'))
        assert response.status_code == 200
        assert len(response.json()['options']) == 4
        assert client.get('/health').json()['data_mode'] == 'DEMO_REFERENCE'

@pytest.mark.parametrize('change',[{'cargo_quantity_tonnes':0},{'cargo_quantity_tonnes':-1},{'origin_port':'Unknown'},{'origin_country':'India'},{'cargo_type':'INVALID'},{'required_arrival_date':'2000-01-01'},{'cargo_quantity_tonnes':1000001}])
def test_api_invalid(shipment,change):
    payload = shipment.model_dump(mode='json') | change
    with TestClient(app) as client:
        assert client.post('/api/shipments/analyze',json=payload).status_code == 422

def test_missing_route(provider, shipment):
    shipment.origin_port='Paradip'
    shipment.origin_country='India'
    with pytest.raises(ValueError,match='No demo maritime route'):
        analyze(shipment,provider,DAY)

def test_sqlite_roundtrip(tmp_path,provider,shipment):
    import sqlite3
    from app.domain.models import Analysis
    a=analyze(shipment,provider,DAY)
    path=tmp_path/'audit.sqlite3'
    AnalysisRepository(path).save(a)
    with sqlite3.connect(path) as db:
        assert Analysis.model_validate_json(db.execute('SELECT payload FROM analyses').fetchone()[0]) == a


def test_deadline_changes_actual_analysis(provider, shipment):
    shipment.cargo_quantity_tonnes = 30000
    long = analyze(shipment, provider, DAY)
    assert long.recommendation.recommended_vessel == 'HANDYSIZE'
    shipment.required_arrival_date = DAY + timedelta(days=26)
    short = analyze(shipment, provider, DAY)
    assert short.recommendation.recommended_vessel == 'PANAMAX'
    assert not short.options[0].voyage.arrival_feasible

@pytest.mark.parametrize('endpoint,key', [('feasibility/check','feasibility'),('voyage/estimate','voyage'),('cost/estimate','cost')])
def test_stage_endpoints(shipment, endpoint, key):
    shipment.required_arrival_date = date.today() + timedelta(days=120)
    with TestClient(app) as client:
        response=client.post('/api/'+endpoint,json=shipment.model_dump(mode='json'))
        assert response.status_code == 200
        assert len(response.json()) == 4
        assert key in response.json()[0]
