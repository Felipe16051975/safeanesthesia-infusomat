import pytest
from services.propofol_service import calculate_propofol

def test_caso_a_propofol_solo():
    """
    Caso A — Propofol solo
    Peso: 4 kg
    Duración: 60 min
    Propofol 1% = 10 mg/ml
    Dosis: 0.05 mg/kg/min
    NaCl: 40 ml
    """
    weight = 4.0
    duration_min = 60.0
    target_dose = 0.05
    diluent = 40.0

    res = calculate_propofol(
        weight=weight,
        target_dose=target_dose,
        duration_min=duration_min,
        species='dog',
        propofol_pct='1%',
        asa_class='I',
        anesthesia_mode='propofol_solo',
        diluent_volume=diluent,
        propofol_dose_unit='mg/kg/min'
    )

    # 12 mg propofol
    assert round(res['total_mg'], 2) == 12.00
    # 1.2 ml propofol
    assert round(res['required_ml'], 2) == 1.20
    # volumen final = 41.2 ml
    assert round(res['final_volume'], 2) == 41.20
    # conc final propofol = 12 / 41.2 = 0.2913 mg/ml
    assert round(res['final_propofol_concentration'], 4) == 0.2913
    # FLOW = 41.2 ml/h
    assert round(res['flow_ml_h'], 2) == 41.20
    # dosis entregada = 0.05 mg/kg/min
    assert round(res['delivered_propofol_mg_kg_min'], 4) == 0.0500
    # VTBI (aunque es de UI, su lógica equivalente)
    assert res['final_volume'] == 41.20

def test_caso_b_ketofol():
    """
    Caso B — Ketofol
    Propofol: 30 mg (3 ml 1%)
    Ketamina: 115 mg (1 ml 115 mg/ml)
    NaCl: 40 ml
    Volumen final: 44 ml
    Duración: 60 min
    """
    weight = 10.0
    duration_min = 60.0
    prop_target = 30.0 / 60.0 / weight
    ket_target = 115.0 / 60.0 / weight

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

    assert round(res['total_mg'], 2) == 30.00
    assert round(res['required_ml'], 2) == 3.00
    assert round(res['ketamine_total_mg'], 2) == 115.00
    assert round(res['ketamine_required_ml'], 2) == 1.00
    assert round(res['final_volume'], 2) == 44.00

    # conc final propofol = 30 / 44 = 0.6818 mg/ml
    assert round(res['final_propofol_concentration'], 4) == 0.6818
    assert round(res['final_ketamine_concentration'], 4) == 2.6136

    # FLOW = 44 ml/h
    assert round(res['flow_ml_h'], 2) == 44.00
    
    # Error menor a 1%
    assert abs(res['delivered_propofol_mg_kg_min'] - prop_target) < (prop_target * 0.01)
    assert abs(res['delivered_ketamine_mg_kg_min'] - ket_target) < (ket_target * 0.01)

def test_caso_c_cambiar_nacl():
    """
    Caso C — Cambiar NaCl no cambia mg totales
    Repetir caso B, pero con NaCl 80 ml.
    """
    weight = 10.0
    duration_min = 60.0
    prop_target = 30.0 / 60.0 / weight
    ket_target = 115.0 / 60.0 / weight

    res_base = calculate_propofol(
        weight=weight, target_dose=prop_target, duration_min=duration_min, species='dog', propofol_pct='1%',
        asa_class='I', anesthesia_mode='propofol_ketamine_mixture', ketamine_concentration=115.0,
        ketamine_target_dose=ket_target, use_ratio_1_2=False, diluent_volume=40.0,
        propofol_dose_unit='mg/kg/min', ketamine_dose_unit='mg/kg/min'
    )

    res_80 = calculate_propofol(
        weight=weight, target_dose=prop_target, duration_min=duration_min, species='dog', propofol_pct='1%',
        asa_class='I', anesthesia_mode='propofol_ketamine_mixture', ketamine_concentration=115.0,
        ketamine_target_dose=ket_target, use_ratio_1_2=False, diluent_volume=80.0,
        propofol_dose_unit='mg/kg/min', ketamine_dose_unit='mg/kg/min'
    )

    # Volumen final cambia.
    assert res_base['final_volume'] != res_80['final_volume']
    assert round(res_80['final_volume'], 2) == 84.00

    # Concentraciones finales bajan.
    assert res_80['final_propofol_concentration'] < res_base['final_propofol_concentration']
    assert res_80['final_ketamine_concentration'] < res_base['final_ketamine_concentration']

    # FLOW cambia.
    assert res_80['flow_ml_h'] != res_base['flow_ml_h']
    assert round(res_80['flow_ml_h'], 2) == 84.00

    # Pero mg totales propofol siguen siendo 30 mg.
    assert round(res_80['total_mg'], 2) == 30.00
    
    # Pero mg totales ketamina siguen siendo 115 mg.
    assert round(res_80['ketamine_total_mg'], 2) == 115.00

    # Dosis entregada sigue coincidiendo
    assert round(res_80['delivered_propofol_mg_kg_min'], 4) == round(prop_target, 4)
    assert round(res_80['delivered_ketamine_mg_kg_min'], 4) == round(ket_target, 4)
