"""
test_phase2_lidocaine.py
Tests for GET /api/lidocaine/meta and POST /api/lidocaine
"""
import pytest
from app import app

def login(client):
    return client.post('/login',
                       data={'username': 'admin', 'password': 'admin123'},
                       follow_redirects=True)


# ── meta endpoint ─────────────────────────────────────────────────────────────

def test_lidocaine_meta_returns_structure():
    client = app.test_client()
    login(client)
    resp = client.get('/api/lidocaine/meta')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    meta = data['meta']
    assert 'concentrations' in meta
    assert 'sites' in meta
    assert 'max_mg_per_kg' in meta
    assert 'classification' in meta

    assert len(meta['concentrations']) > 0
    assert len(meta['sites']) > 0
    assert 'dog' in meta['max_mg_per_kg']
    assert 'cat' in meta['max_mg_per_kg']


def test_lidocaine_meta_unauthenticated_redirects():
    client = app.test_client()
    resp = client.get('/api/lidocaine/meta')
    assert resp.status_code in (302, 401, 403)


# ── calculation endpoint ──────────────────────────────────────────────────────

def test_lidocaine_calculates_mg_administrados():
    client = app.test_client()
    login(client)
    resp = client.post('/api/lidocaine', json={
        'weight': 10.0,
        'species': 'dog',
        'targetLimitDose': 8.0,
        'concentrationMgMl': 20.0,
        'lineaAlbaMl': 1.0,
        'ligamentoMl': 0.5,
        'peritonealMl': 0,
        'pielMl': 0.5,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    lido = data['lidocaine']
    
    # Total ml = 1.0 + 0.5 + 0.5 = 2.0 ml
    assert lido['total_injected_ml'] == pytest.approx(2.0)
    # Total mg = 2.0 ml * 20 mg/ml = 40.0 mg
    assert lido['total_injected_mg'] == pytest.approx(40.0)
    # Accumulated mg is an alias for total_injected_mg
    assert lido['accumulated_mg'] == pytest.approx(40.0)


def test_lidocaine_calculates_remaining_mg():
    client = app.test_client()
    login(client)
    resp = client.post('/api/lidocaine', json={
        'weight': 10.0,
        'species': 'dog',
        'targetLimitDose': 8.0,
        'concentrationMgMl': 20.0,
        'lineaAlbaMl': 1.0,
        'ligamentoMl': 0.5,
        'peritonealMl': 0,
        'pielMl': 0.5,
    })
    lido = resp.get_json()['lidocaine']
    # Max allowed mg = 10 kg * 8 mg/kg = 80 mg
    # Total injected mg = 40 mg
    # Remaining = 80 - 40 = 40 mg
    assert lido['remaining_mg'] == pytest.approx(40.0)


def test_lidocaine_calculates_percentage_of_max():
    client = app.test_client()
    login(client)
    resp = client.post('/api/lidocaine', json={
        'weight': 10.0,
        'species': 'dog',
        'targetLimitDose': 8.0,
        'concentrationMgMl': 20.0,
        'lineaAlbaMl': 2.0,
        'ligamentoMl': 0,
        'peritonealMl': 0,
        'pielMl': 0,
    })
    lido = resp.get_json()['lidocaine']
    # Max allowed = 80 mg
    # Injected = 2 * 20 = 40 mg
    # Pct = 40/80 * 100 = 50%
    assert lido['pct_of_max'] == pytest.approx(50.0)


def test_lidocaine_returns_site():
    client = app.test_client()
    login(client)
    resp = client.post('/api/lidocaine', json={
        'weight': 10.0,
        'species': 'dog',
        'targetLimitDose': 8.0,
        'concentrationMgMl': 20.0,
        'lineaAlbaMl': 1.0,
        'site': 'línea alba'
    })
    lido = resp.get_json()['lidocaine']
    assert lido['site'] == 'línea alba'


def test_lidocaine_safe_classification():
    """Pct < safe threshold (70%) → SAFE"""
    client = app.test_client()
    login(client)
    # Max = 80mg. Inject = 20mg (1ml*20). Pct = 25%.
    resp = client.post('/api/lidocaine', json={
        'weight': 10.0, 'species': 'dog', 'targetLimitDose': 5.0,
        'concentrationMgMl': 20.0, 'lineaAlbaMl': 1.0
    })
    lido = resp.get_json()['lidocaine']
    assert lido['status'] == 'SAFE'


def test_lidocaine_warning_classification():
    """Pct >= 90% and < 100% → WARNING"""
    client = app.test_client()
    login(client)
    # Max = 50mg. Inject = 47.5mg (2.375ml*20). Pct = 95%.
    resp = client.post('/api/lidocaine', json={
        'weight': 10.0, 'species': 'dog', 'targetLimitDose': 5.0,
        'concentrationMgMl': 20.0, 'lineaAlbaMl': 2.375
    })
    lido = resp.get_json()['lidocaine']
    assert lido['status'] == 'WARNING'


def test_lidocaine_critical_classification():
    """Pct >= 100% → CRITICAL"""
    client = app.test_client()
    login(client)
    # Max = 50mg. Inject = 50mg (2.5ml*20). Pct = 100%.
    resp = client.post('/api/lidocaine', json={
        'weight': 10.0, 'species': 'dog', 'targetLimitDose': 5.0,
        'concentrationMgMl': 20.0, 'lineaAlbaMl': 2.5
    })
    lido = resp.get_json()['lidocaine']
    assert lido['status'] == 'CRITICAL'


def test_lidocaine_exceeds_species_toxic_limit():
    """If targetLimitDose > toxic limit (e.g. 5 for dog), gives warning"""
    client = app.test_client()
    login(client)
    resp = client.post('/api/lidocaine', json={
        'weight': 10.0, 'species': 'dog', 'targetLimitDose': 10.0,
        'concentrationMgMl': 20.0, 'lineaAlbaMl': 1.0
    })
    lido = resp.get_json()['lidocaine']
    assert lido['status'] == 'WARNING'
    # Checking that the alert is present
    has_toxic_alert = any("límite tóxico" in a for a in lido['alerts'])
    assert has_toxic_alert


def test_lidocaine_zero_weight_returns_400():
    client = app.test_client()
    login(client)
    resp = client.post('/api/lidocaine', json={
        'weight': 0, 'species': 'dog', 'targetLimitDose': 8.0,
        'concentrationMgMl': 20.0, 'lineaAlbaMl': 1.0
    })
    assert resp.status_code == 400
    assert resp.get_json()['success'] is False
