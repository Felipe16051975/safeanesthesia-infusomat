import pytest
from services.hospital_fluids_service import calculate_hospital_fluids

def test_maintenance_dog():
    res = calculate_hospital_fluids(weight_kg=10, species="dog", dehydration_pct=0, losses_ml=0, replacement_hours=24)
    # 10 kg dog * 60 ml/kg/day = 600 ml/day
    assert res["maintenance_ml_day"] == 600
    assert res["maintenance_ml_h"] == 25  # 600 / 24

def test_maintenance_cat():
    res = calculate_hospital_fluids(weight_kg=5, species="cat", dehydration_pct=0, losses_ml=0, replacement_hours=24)
    # 5 kg cat * 60 ml/kg/day = 300 ml/day (midpoint of 50-70 ml/kg/día range)
    assert res["maintenance_ml_day"] == 300
    assert res["maintenance_ml_h"] == round(300/24, 2)

def test_dehydration_deficit():
    # 10 kg dog with 5% dehydration
    res = calculate_hospital_fluids(weight_kg=10, species="dog", dehydration_pct=5, losses_ml=0, replacement_hours=24)
    # deficit = 10 * 0.05 * 1000 = 500 ml
    assert res["deficit_ml"] == 500

def test_losses_and_total_volume():
    # 10 kg dog, 5% dehy, 100 ml losses, over 6 hours
    res = calculate_hospital_fluids(weight_kg=10, species="dog", dehydration_pct=5, losses_ml=100, replacement_hours=6)
    # Maint day = 600, Maint h = 25
    # Maint in 6h = 150
    # Deficit = 500
    # Losses = 100
    # Total = 150 + 500 + 100 = 750
    assert res["total_volume_in_period"] == 750
    assert res["flow_ml_h"] == 750 / 6
    assert res["vtbi_ml"] == 750
