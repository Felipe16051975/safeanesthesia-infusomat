"""
test_phase2_ketamine.py
Tests for GET /api/ketamine/meta and POST /api/ketamine
"""
import pytest
from app import app

def login(client):
    return client.post('/login',
                       data={'username': 'admin', 'password': 'admin123'},
                       follow_redirects=True)


# ── meta endpoint ─────────────────────────────────────────────────────────────

def test_ketamine_meta_returns_concentrations():
    client = app.test_client()
    login(client)
    resp = client.get('/api/ketamine/meta')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    meta = data['meta']
    assert 'concentrations' in meta
    assert len(meta['concentrations']) > 0
    # Each concentration must have name and value_mg_per_ml
    for c in meta['concentrations']:
        assert 'name' in c
        assert 'value_mg_per_ml' in c


def test_ketamine_meta_returns_reasons():
    client = app.test_client()
    login(client)
    resp = client.get('/api/ketamine/meta')
    data = resp.get_json()
    meta = data['meta']
    assert 'reasons' in meta
    assert len(meta['reasons']) > 0


def test_ketamine_meta_returns_limits():
    client = app.test_client()
    login(client)
    resp = client.get('/api/ketamine/meta')
    data = resp.get_json()
    meta = data['meta']
    assert 'limits' in meta
    assert 'dog' in meta['limits']
    assert 'cat' in meta['limits']
    for species in ['dog', 'cat']:
        for key in ['safe', 'warning', 'critical']:
            assert key in meta['limits'][species]


def test_ketamine_meta_unauthenticated_redirects():
    client = app.test_client()
    resp = client.get('/api/ketamine/meta')
    assert resp.status_code in (302, 401, 403)


# ── calculation endpoint ──────────────────────────────────────────────────────

def test_ketamine_calculates_mg_and_ml():
    client = app.test_client()
    login(client)
    resp = client.post('/api/ketamine', json={
        'weight': 10.0,
        'targetDose': 0.5,
        'concentrationMgMl': 50.0,
        'species': 'dog',
        'reason': 'tracción ovárica',
        'accumulatedMg': 0.0,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    k = data['ketamine']
    # 10 kg × 0.5 mg/kg = 5 mg; 5 mg / 50 mg/ml = 0.1 ml
    assert k['bolus_mg'] == pytest.approx(5.0)
    assert k['bolus_ml'] == pytest.approx(0.1)


def test_ketamine_returns_concentration_used():
    client = app.test_client()
    login(client)
    resp = client.post('/api/ketamine', json={
        'weight': 10.0, 'targetDose': 0.5, 'concentrationMgMl': 100.0,
        'species': 'dog', 'accumulatedMg': 0.0
    })
    k = resp.get_json()['ketamine']
    assert k['concentration_mg_ml'] == pytest.approx(100.0)
    # 10 × 0.5 / 100 = 0.05 ml
    assert k['bolus_ml'] == pytest.approx(0.05)


def test_ketamine_accumulation_tracked():
    client = app.test_client()
    login(client)
    resp = client.post('/api/ketamine', json={
        'weight': 10.0, 'targetDose': 0.5, 'concentrationMgMl': 50.0,
        'species': 'dog', 'accumulatedMg': 3.0
    })
    k = resp.get_json()['ketamine']
    assert k['accumulated_mg'] == pytest.approx(3.0)
    assert k['new_accumulated_mg'] == pytest.approx(8.0)   # 3 + 5


def test_ketamine_reinforcement_index():
    client = app.test_client()
    login(client)
    resp = client.post('/api/ketamine', json={
        'weight': 10.0, 'targetDose': 0.5, 'concentrationMgMl': 50.0,
        'species': 'dog', 'accumulatedMg': 0.0
    })
    k = resp.get_json()['ketamine']
    # safe limit for dog = 2 mg; bolus = 5 mg; index = (0+5)/2 = 2.5
    assert k['reinforcement_index'] == pytest.approx(2.5)


def test_ketamine_reason_returned():
    client = app.test_client()
    login(client)
    resp = client.post('/api/ketamine', json={
        'weight': 10.0, 'targetDose': 0.5, 'concentrationMgMl': 50.0,
        'species': 'dog', 'reason': 'movimiento', 'accumulatedMg': 0.0
    })
    k = resp.get_json()['ketamine']
    assert k['reason'] == 'movimiento'


def test_ketamine_safe_classification():
    """Bolus < safe limit (2 mg for dog) → SAFE"""
    client = app.test_client()
    login(client)
    # 1 kg × 1.5 mg/kg = 1.5 mg < 2 mg safe limit
    resp = client.post('/api/ketamine', json={
        'weight': 1.0, 'targetDose': 1.5, 'concentrationMgMl': 50.0,
        'species': 'dog', 'accumulatedMg': 0.0
    })
    k = resp.get_json()['ketamine']
    assert k['classification'] == 'SAFE'


def test_ketamine_warning_classification():
    """Bolus between warning (5) and critical (10) for dog → WARNING"""
    client = app.test_client()
    login(client)
    # 10 kg × 0.6 mg/kg = 6 mg (≥ 5 warning, < 10 critical)
    resp = client.post('/api/ketamine', json={
        'weight': 10.0, 'targetDose': 0.6, 'concentrationMgMl': 50.0,
        'species': 'dog', 'accumulatedMg': 0.0
    })
    k = resp.get_json()['ketamine']
    assert k['classification'] == 'WARNING'


def test_ketamine_critical_classification():
    """Bolus ≥ critical (10 mg for dog) → CRITICAL"""
    client = app.test_client()
    login(client)
    # 20 kg × 0.6 mg/kg = 12 mg ≥ 10
    resp = client.post('/api/ketamine', json={
        'weight': 20.0, 'targetDose': 0.6, 'concentrationMgMl': 50.0,
        'species': 'dog', 'accumulatedMg': 0.0
    })
    k = resp.get_json()['ketamine']
    assert k['classification'] == 'CRITICAL'


def test_ketamine_zero_weight_returns_400():
    client = app.test_client()
    login(client)
    resp = client.post('/api/ketamine', json={
        'weight': 0, 'targetDose': 0.5, 'concentrationMgMl': 50.0,
        'species': 'dog', 'accumulatedMg': 0.0
    })
    assert resp.status_code == 400
    assert resp.get_json()['success'] is False
