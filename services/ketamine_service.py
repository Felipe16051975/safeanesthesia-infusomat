import os
import json

# RUTA ABSOLUTA PARA ACCEDER A CONFIGURACIONES DESDE EL SERVICIO
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'ketamine_limits.json')

def load_limits():
    """Carga dinámicamente los límites de ketamina desde el JSON configurado."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {
            "limits": {
                "defaultConcentration": 50.0, # 5% = 50 mg/ml
                "maxBoloDose": 2.0,          # mg/kg
                "suggestedBoloDose": 0.5     # mg/kg
            }
        }

def calculate_ketamine_reinforcement(weight, target_dose_mg_kg, concentration_mg_ml=None):
    """
    Calcula el bolo de ketamina recomendado para refuerzo analgésico transoperatorio.
    
    Parámetros:
      - weight: Peso del paciente en kg (>0)
      - target_dose_mg_kg: Dosis objetivo en bolo (mg/kg)
      - concentration_mg_ml: Concentración disponible (mg/ml), si es None se lee del JSON
      
    Retorna:
      - Diccionario con mg totales, ml calculados y advertencias correspondientes.
    """
    if weight <= 0:
        raise ValueError("El peso debe ser mayor a 0 kg.")
        
    limits_data = load_limits()
    limits = limits_data["limits"]
    
    if concentration_mg_ml is None or concentration_mg_ml <= 0:
        concentration_mg_ml = limits["defaultConcentration"]
        
    total_mg = weight * target_dose_mg_kg
    volume_ml = total_mg / concentration_mg_ml
    
    alerts = []
    if target_dose_mg_kg > limits["maxBoloDose"]:
        alerts.append({
            "type": "ketamine_max_exceeded",
            "message": f"Dosis de ketamina ingresada ({target_dose_mg_kg} mg/kg) supera la recomendación segura de {limits['maxBoloDose']} mg/kg para un bolo único de mantenimiento."
        })
        
    return {
        "required_mg": round(total_mg, 2),
        "required_ml": round(volume_ml, 3),
        "concentration_used_mg_ml": concentration_mg_ml,
        "alerts": alerts,
        "clinical_reminder": "Administrar sólo bajo criterio veterinario y monitorización cardiorrespiratoria estricta ante estímulo quirúrgico previsto.",
        "metadata_version": limits_data.get("_metadata", {}).get("version", "1.0")
    }
