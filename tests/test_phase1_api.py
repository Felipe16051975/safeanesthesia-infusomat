import json
import pytest
from app import app

# Helper to login via test client
def login(client, username='admin', password='admin123'):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

def test_unauthenticated_access():
    client = app.test_client()
    response = client.post('/api/calculate', json={})
    # Flask-Login redirects to login view (302) for unauthenticated requests
    assert response.status_code in (302, 401, 403)

def test_successful_login_and_calculation():
    client = app.test_client()
    # Perform login
    resp_login = login(client)
    assert resp_login.status_code == 200

    payload = {
        "patientName": "Luna",
        "species": "cat",
        "weight": 5,
        "age": "1 año",
        "asa": "II",
        "surgeryType": "OVH",
        "durationMin": 60,
        "propofolConcentration": 1,
        "targetDose": 0.2,
        "diluentVolume": 40,
        "linePrimed": "si",
        "primedWith": "suero",
        "deadVolume": 5
    }
    resp = client.post('/api/calculate', json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    prop = data['propofol']
    pump = data['pump']
    # Propofol assertions
    assert prop['mg_per_min'] == pytest.approx(1.0)
    assert prop['mg_per_hour'] == pytest.approx(60.0)
    assert prop['mg_total'] == pytest.approx(60.0)
    assert prop['ml_propofol'] == pytest.approx(6.0)
    assert prop['volume_final'] == pytest.approx(46.0)
    assert prop['final_concentration_mg_ml'] == pytest.approx(1.3043478, rel=1e-3)
    assert prop['flow_ml_h'] == pytest.approx(46.0)
    # Pump assertions
    assert pump['flow_ml_h'] == pytest.approx(46.0)
    assert pump['vtbi_ml'] == pytest.approx(46.0)
    assert pump['time_min'] == 60
    assert pump['priming_delay_min'] == pytest.approx(6.521739130434783, rel=1e-3)

def test_error_on_invalid_weight():
    client = app.test_client()
    login(client)  # ensure authenticated
    payload = {
        "patientName": "Luna",
        "species": "cat",
        "weight": 0,
        "age": "1 año",
        "asa": "II",
        "surgeryType": "OVH",
        "durationMin": 60,
        "propofolConcentration": 1,
        "targetDose": 0.2,
        "diluentVolume": 40,
        "linePrimed": "si",
        "primedWith": "suero",
        "deadVolume": 5
    }
    resp = client.post('/api/calculate', json=payload)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['success'] is False
    assert 'error' in data
