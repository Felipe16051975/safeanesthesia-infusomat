"""
test_phase2_start_procedure.py
Tests for POST /api/start-procedure and GET /api/procedure/<id>/events
"""
import json
import pytest
from app import app

# ── helper ────────────────────────────────────────────────────────────────────
def login(client):
    return client.post('/login',
                       data={'username': 'admin', 'password': 'admin123'},
                       follow_redirects=True)


# ── start-procedure ───────────────────────────────────────────────────────────

def test_start_procedure_returns_procedure_id():
    client = app.test_client()
    login(client)
    resp = client.post('/api/start-procedure', json={
        'patientName': 'Simba',
        'species': 'cat',
        'weight': 4.5
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['success'] is True
    assert isinstance(data['procedure_id'], int)
    assert data['procedure_id'] > 0


def test_start_procedure_zero_weight_returns_400():
    client = app.test_client()
    login(client)
    resp = client.post('/api/start-procedure', json={
        'patientName': 'Simba',
        'species': 'cat',
        'weight': 0
    })
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['success'] is False
    assert 'error' in data


def test_start_procedure_unauthenticated_redirects():
    client = app.test_client()
    resp = client.post('/api/start-procedure', json={
        'patientName': 'Simba', 'species': 'cat', 'weight': 4.5
    })
    assert resp.status_code in (302, 401, 403)


# ── events endpoint ───────────────────────────────────────────────────────────

def test_events_returns_empty_for_new_procedure():
    client = app.test_client()
    login(client)
    # Start a fresh procedure
    resp = client.post('/api/start-procedure', json={
        'patientName': 'Rocky', 'species': 'dog', 'weight': 10.0
    })
    proc_id = resp.get_json()['procedure_id']

    events_resp = client.get(f'/api/procedure/{proc_id}/events')
    assert events_resp.status_code == 200
    data = events_resp.get_json()
    assert data['success'] is True
    assert data['procedure_id'] == proc_id
    assert data['events'] == []


def test_events_accumulate_after_ketamine_and_lidocaine():
    client = app.test_client()
    login(client)

    # Start procedure
    proc_id = client.post('/api/start-procedure', json={
        'patientName': 'Rex', 'species': 'dog', 'weight': 20.0
    }).get_json()['procedure_id']

    # Add a ketamine event
    client.post('/api/ketamine', json={
        'weight': 20.0, 'targetDose': 0.5, 'concentrationMgMl': 50,
        'species': 'dog', 'reason': 'tracción ovárica',
        'accumulatedMg': 0, 'procedureId': proc_id
    })

    # Add a lidocaine event
    client.post('/api/lidocaine', json={
        'weight': 20.0, 'species': 'dog', 'targetLimitDose': 5.0,
        'concentrationMgMl': 20, 'lineaAlbaMl': 1.0,
        'ligamentoMl': 0.5, 'peritonealMl': 0, 'pielMl': 0,
        'site': 'línea alba', 'procedureId': proc_id
    })

    # Retrieve events
    events_resp = client.get(f'/api/procedure/{proc_id}/events')
    assert events_resp.status_code == 200
    data = events_resp.get_json()
    assert data['success'] is True
    event_types = [e['event_type'] for e in data['events']]
    assert 'ketamine_bolus' in event_types
    assert 'lidocaine_block' in event_types
