import pytest
from services.hospital_cri_service import calculate_hospital_cri

def test_cri_mg_kg_h():
    # 10 kg dog, 2 mg/kg/h metoclopramida
    # conc = 5 mg/ml, final_vol = 100 ml, duration = 24 h
    res = calculate_hospital_cri(
        weight_kg=10, dose=2, unit="mg/kg/h",
        concentration_mg_ml=5, final_volume_ml=100, duration_hours=24
    )
    # Total mg = 2 * 10 * 24 = 480 mg
    assert res["total_mg"] == 480
    # ml a extraer = 480 / 5 = 96 ml
    assert res["drug_ml"] == 96
    # base_fluid = 100 - 96 = 4 ml
    assert res["base_fluid_ml"] == 4
    # FLOW = 100 / 24 = 4.17
    assert res["flow_ml_h"] == round(100/24, 2)
    assert res["vtbi_ml"] == 100

def test_cri_mcg_kg_min():
    # 10 kg dog, 5 mcg/kg/min dopamina
    # conc = 40 mg/ml, final_vol = 250 ml, duration = 12 h
    res = calculate_hospital_cri(
        weight_kg=10, dose=5, unit="mcg/kg/min",
        concentration_mg_ml=40, final_volume_ml=250, duration_hours=12
    )
    # mcg/min = 5 * 10 = 50 mcg/min
    # total_mcg = 50 * (12 * 60) = 36000 mcg = 36 mg
    assert res["total_mg"] == 36
    assert res["drug_ml"] == 36 / 40 # 0.9 ml
    assert res["base_fluid_ml"] == 250 - 0.9
    assert res["flow_ml_h"] == round(250/12, 2)

def test_cri_mg_kg_day():
    # 10 kg dog, 2 mg/kg/day
    # conc = 10 mg/ml, final_vol = 100, duration = 12 h (half a day)
    res = calculate_hospital_cri(
        weight_kg=10, dose=2, unit="mg/kg/day",
        concentration_mg_ml=10, final_volume_ml=100, duration_hours=12
    )
    # Total mg day = 20 mg
    # For 12 hours = 10 mg
    assert res["total_mg"] == 10
    assert res["drug_ml"] == 1
    assert res["base_fluid_ml"] == 99
