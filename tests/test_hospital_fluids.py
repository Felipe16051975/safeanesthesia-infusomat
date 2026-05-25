import pytest
from services.hospital_fluids_service import calculate_fluid_therapy, get_fluid_recommendation

def test_fluid_therapy_calculation():
    """
    - Fluidoterapia base: déficit + mantención + pérdidas.
    - 50 ml/kg/día
    """
    # Perro 10 kg, deshidratación 5%, perdidas 100ml
    weight_kg = 10
    dehydration_percent = 5
    losses = 100
    
    res = calculate_fluid_therapy(
        weight_kg, dehydration_percent, losses,
        main_problem="Gastroenteritis", renal_state="Normal", hepatic_state="Normal"
    )
    
    # deficit = 10 * 5 * 10 = 500
    assert res['deficit_ml'] == 500
    # maintenance = 10 * 50 = 500
    assert res['maintenance_ml'] == 500
    # continuous = 100
    assert res['continuous_losses_ml'] == 100
    # total = 1100
    assert res['total_volume_ml'] == 1100
    # flow_ml_h = 1100 / 24 = 45.83
    assert res['flow_ml_h'] == round(1100 / 24, 2)
    
    assert res['recommendation']['fluid'] == "Ringer Lactato"

def test_fluid_recommendation_renal():
    res = get_fluid_recommendation(
        main_problem="Otro", renal_state="Oliguria", hepatic_state="Normal"
    )
    assert res['fluid'] == "NaCl 0,9%"
