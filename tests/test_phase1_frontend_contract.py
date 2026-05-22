import re
import sys, os
# Ensure project root is in PYTHONPATH for imports
project_root = os.path.abspath(os.path.join(__file__, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from app import app

# Helper login function
def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )

def test_login_page_contains_form_and_inputs():
    client = app.test_client()
    resp = client.get("/login")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert re.search(r"<form", html, re.IGNORECASE)
    assert re.search(r"<input[^>]*name=[\"']?username[\"']?", html, re.IGNORECASE)
    assert re.search(r"<input[^>]*name=[\"']?password[\"']?", html, re.IGNORECASE)

def test_root_redirect_to_login_when_unauthenticated():
    client = app.test_client()
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 301)
    loc = resp.headers.get("Location", "")
    assert "/login" in loc

def test_homepage_contains_form_ids_after_login():
    client = app.test_client()
    login_resp = login(client)
    assert login_resp.status_code == 200
    resp = client.get("/", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    required_ids = [
        "patientName",
        "species",
        "weight",
        "age",
        "asa",
        "surgeryType",
        "durationMin",
        "propofolConcentration",
        "targetDose",
        "diluentVolumePreset",
        "linePrimed",
        "primedWith",
        "deadVolume",
        "btn-run-calculation",
    ]
    for id_ in required_ids:
        assert f'id="{id_}"' in html, f"Missing id {id_}"

def test_homepage_contains_result_ids():
    client = app.test_client()
    login(client)
    resp = client.get("/", follow_redirects=True)
    html = resp.get_data(as_text=True)
    result_ids = [
        "out-propofol-pure",
        "out-saline-diluent",
        "out-mixture-volume",
        "out-mixture-concentration",
        "out-propofol-total-mg",
        "pump-flow-val",
        "pump-vtbi-val",
        "pump-time-val",
        "out-priming-delay",
        "alerts-container",
    ]
    for rid in result_ids:
        assert f'id="{rid}"' in html, f"Missing result id {rid}"

def test_static_resources_loaded():
    client = app.test_client()
    js_resp = client.get("/static/js/app.js")
    assert js_resp.status_code == 200
    assert "fetch(\"/api/calculate\"" in js_resp.get_data(as_text=True)
    css_resp = client.get("/static/css/styles.css")
    assert css_resp.status_code == 200

def test_js_contains_expected_payload_fields():
    client = app.test_client()
    js_content = client.get("/static/js/app.js").get_data(as_text=True)
    fields = [
        "weight",
        "durationMin",
        "targetDose",
        "propofolConcentration",
        "diluentVolume",
        "linePrimed",
        "primedWith",
        "deadVolume",
        "species",
        "asa",
    ]
    for field in fields:
        assert re.search(rf"['\"]?{field}['\"]?\s*:\s*", js_content), f"Field {field} not sent in fetch"

def test_api_calculation_returns_expected_values():
    client = app.test_client()
    login(client)
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
        "deadVolume": 5,
    }
    resp = client.post("/api/calculate", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    prop = data["propofol"]
    pump = data["pump"]
    assert prop["mg_per_min"] == pytest.approx(1.0)
    assert prop["mg_per_hour"] == pytest.approx(60.0)
    assert prop["mg_total"] == pytest.approx(60.0)
    assert prop["ml_propofol"] == pytest.approx(6.0)
    assert prop["volume_final"] == pytest.approx(46.0)
    assert prop["final_concentration_mg_ml"] == pytest.approx(1.3043478, rel=1e-3)
    assert prop["flow_ml_h"] == pytest.approx(46.0)
    assert pump["flow_ml_h"] == pytest.approx(46.0)
    assert pump["vtbi_ml"] == pytest.approx(46.0)
    assert pump["time_min"] == 60
    assert pump["priming_delay_min"] == pytest.approx(6.521739130434783, rel=1e-3)
