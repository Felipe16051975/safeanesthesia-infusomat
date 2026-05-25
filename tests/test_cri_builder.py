import pytest
from services.hospital_cri_service import build_cri

def test_tlk_500ml_bag():
    """
    Test mandatory requirements:
    1. TLK en bolsa 500 ml:
    - Tramadol objetivo 300 mg/L (comercial 100 mg/ml) -> 1.5 ml
    - Lidocaína objetivo 1000 mg/L (comercial 20 mg/ml) -> 25 ml
    - Ketamina objetivo 200 mg/L (comercial 100 mg/ml) -> 1 ml
    - calcular ml a agregar según concentración comercial
    - volumen a retirar = suma ml agregados = 27.5 ml
    - volumen final = 500 ml
    """
    drugs_input = [
        {'id': 'tramadol', 'target_mg_L': 300, 'commercial_mg_ml': 100},
        {'id': 'lidocaine', 'target_mg_L': 1000, 'commercial_mg_ml': 20},
        {'id': 'ketamine', 'target_mg_L': 200, 'commercial_mg_ml': 100}
    ]
    
    result = build_cri(drugs_input, bag_volume_ml=500, species='dog')
    
    # Validation
    assert result['final_bag_volume_ml'] == 500
    assert result['volume_to_withdraw_ml'] == 27.5
    
    t_res = result['drugs']['tramadol']
    assert t_res['mg_needed'] == 150.0
    assert t_res['ml_to_add'] == 1.5
    assert t_res['diff_percent'] < 1.0
    
    l_res = result['drugs']['lidocaine']
    assert l_res['mg_needed'] == 500.0
    assert l_res['ml_to_add'] == 25.0
    assert l_res['diff_percent'] < 1.0
    
    k_res = result['drugs']['ketamine']
    assert k_res['mg_needed'] == 100.0
    assert k_res['ml_to_add'] == 1.0
    assert k_res['diff_percent'] < 1.0
