import pytest
from services.propofol_service import calculate_propofol

def test_v1c1_dilution_logic():
    """
    Valida la lógica de V1C1, verificando que la dilución no altere
    la dosis total y que la concentración final sea correcta.
    """
    # CASO DE PRUEBA MANUAL:
    # Propofol: 30 mg -> 3 ml (1% o 10 mg/ml)
    # Ketamina: 115 mg -> 1 ml (115 mg/ml)
    # NaCl: 40 ml
    # V_final = 44 ml
    
    weight = 10.0
    duration_min = 60.0
    prop_target = 30.0 / 60.0 / weight  # 0.05 mg/kg/min
    ket_target = 115.0 / 60.0 / weight  # ~0.1917 mg/kg/min
    
    res = calculate_propofol(
        weight=weight,
        target_dose=prop_target,
        duration_min=duration_min,
        species='dog',
        propofol_pct='1%',
        asa_class='I',
        anesthesia_mode='propofol_ketamine_mixture',
        ketamine_concentration=115.0,
        ketamine_target_dose=ket_target,
        use_ratio_1_2=False,
        diluent_volume=40.0,
        propofol_dose_unit='mg/kg/min',
        ketamine_dose_unit='mg/kg/min'
    )
    
    # 1. V1C1 propofol
    assert round(res['total_mg'], 2) == 30.00
    assert round(res['required_ml'], 2) == 3.00
    assert round(res['final_volume'], 2) == 44.00
    assert round(res['final_propofol_concentration'], 4) == round(30.0 / 44.0, 4)
    
    # 2. V1C1 ketamina
    assert round(res['ketamine_total_mg'], 2) == 115.00
    assert round(res['ketamine_required_ml'], 2) == 1.00
    assert round(res['final_ketamine_concentration'], 4) == round(115.0 / 44.0, 4)
    
    # 3. Dosis entregada
    # Si duration = 60 min y volumen final = 44 ml, FLOW = 44 ml/h
    assert res['flow_ml_h'] == 44.00
    
    # 4. Dosis objetivo coincide con entregada (validación estricta < 1%)
    assert res['target_propofol_mg_kg_min'] == res['delivered_propofol_mg_kg_min']
    assert res['target_ketamine_mg_kg_min'] == res['delivered_ketamine_mg_kg_min']

def test_changing_nacl_does_not_change_mg():
    """
    Verifica que cambiar el NaCl modifica la concentración final pero NO altera
    la dosis entregada real (mg/kg/min) ni los mg totales.
    """
    res1 = calculate_propofol(
        weight=10.0, target_dose=0.1, duration_min=60.0, species='dog', propofol_pct='1%',
        asa_class='I', diluent_volume=40.0
    )
    res2 = calculate_propofol(
        weight=10.0, target_dose=0.1, duration_min=60.0, species='dog', propofol_pct='1%',
        asa_class='I', diluent_volume=80.0
    )
    
    # Mismos mg totales
    assert res1['total_mg'] == res2['total_mg']
    assert res1['required_ml'] == res2['required_ml']
    
    # Diferente volumen y concentración
    assert res1['final_volume'] != res2['final_volume']
    assert res1['final_propofol_concentration'] != res2['final_propofol_concentration']
    
    # Pero misma dosis entregada al paciente
    assert res1['delivered_propofol_mg_kg_min'] == res2['delivered_propofol_mg_kg_min']
