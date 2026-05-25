import json
import os

def load_drugs_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'drugs_cri.json')
    if not os.path.exists(config_path):
        return {}
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_cri(drugs_input, bag_volume_ml, species):
    """
    drugs_input: list of dicts: [{'id': 'lidocaine', 'target_mg_L': 1000, 'commercial_mg_ml': 20}, ...]
    """
    config = load_drugs_config()
    
    results = {}
    total_ml_to_add = 0.0
    warnings = []
    
    for d in drugs_input:
        drug_id = d['id']
        target_mg_L = float(d['target_mg_L'])
        commercial_mg_ml = float(d['commercial_mg_ml'])
        
        drug_info = config.get(drug_id, {})
        
        # Check warnings
        if species in drug_info.get('warning_species', {}):
            warnings.append(drug_info['warning_species'][species])
            
        # Calculation
        # mg necesarios = (concentración objetivo mg/L / 1000) * volumen bolsa ml
        mg_needed = (target_mg_L / 1000.0) * bag_volume_ml
        
        # ml a agregar = mg necesarios / concentración comercial mg/ml
        ml_to_add = mg_needed / commercial_mg_ml if commercial_mg_ml > 0 else 0
        
        total_ml_to_add += ml_to_add
        
        # Validation
        final_concentration_mg_L = (mg_needed / bag_volume_ml) * 1000 if bag_volume_ml > 0 else 0
        final_concentration_mg_ml = mg_needed / bag_volume_ml if bag_volume_ml > 0 else 0
        
        diff_percent = abs(final_concentration_mg_L - target_mg_L) / target_mg_L * 100 if target_mg_L > 0 else 0
        
        results[drug_id] = {
            "name": drug_info.get('name', drug_id),
            "target_mg_L": target_mg_L,
            "commercial_mg_ml": commercial_mg_ml,
            "mg_needed": round(mg_needed, 2),
            "ml_to_add": round(ml_to_add, 2),
            "final_concentration_mg_L": round(final_concentration_mg_L, 2),
            "final_concentration_mg_ml": round(final_concentration_mg_ml, 4),
            "diff_percent": round(diff_percent, 4)
        }
        
    return {
        "drugs": results,
        "volume_to_withdraw_ml": round(total_ml_to_add, 2),
        "final_bag_volume_ml": round(bag_volume_ml, 2),
        "warnings": warnings
    }
