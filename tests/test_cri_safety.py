import pytest
from services.hospital_cri_service import build_cri

def test_cat_lidocaine_warning():
    """
    6. Gato + lidocaína:
    - mostrar advertencia fuerte
    - no bloquear
    """
    drugs_input = [
        {'id': 'lidocaine', 'target_mg_L': 1000, 'commercial_mg_ml': 20}
    ]
    
    # Debe procesar correctamente sin error/excepción
    result = build_cri(drugs_input, bag_volume_ml=500, species='cat')
    
    assert 'lidocaine' in result['drugs']
    assert result['drugs']['lidocaine']['ml_to_add'] == 25.0
    
    # Debe existir la advertencia fuerte
    assert any("No se recomienda CRI de lidocaína en gatos" in w for w in result['warnings'])
