import os
import json

# RUTA ABSOLUTA PARA ACCEDER A CONFIGURACIONES DESDE EL SERVICIO
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'lidocaine_limits.json')

def load_limits():
    """Carga los límites de lidocaína desde el JSON configurado."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {
            "limits": {
                "dog": {
                    "maxSafeDose": 8.0 # mg/kg
                },
                "cat": {
                    "maxSafeDose": 4.0 # mg/kg
                }
            }
        }

def calculate_lidocaine_limit(weight, species, concentration_pct=2.0):
    """
    Calcula la dosis máxima de lidocaína segura por peso y especie.
    
    Parámetros:
      - weight: Peso en kg (>0)
      - species: 'dog' o 'cat'
      - concentration_pct: Concentración en porcentaje (por defecto 2.0% = 20 mg/ml)
      
    Retorna:
      - Diccionario con dosis máxima en mg y ml.
    """
    if weight <= 0:
        raise ValueError("El peso debe ser mayor a 0 kg.")
        
    limits_data = load_limits()
    limits = limits_data["limits"].get(species, limits_data["limits"]["dog"])
    max_safe_dose_mg_kg = limits["maxSafeDose"]
    
    # 2.0% -> 20 mg/ml; 1.0% -> 10 mg/ml, etc.
    concentration_mg_ml = concentration_pct * 10.0
    
    max_safe_mg = weight * max_safe_dose_mg_kg
    max_safe_ml = max_safe_mg / concentration_mg_ml if concentration_mg_ml > 0 else 0.0
    
    return {
        "max_safe_mg": round(max_safe_mg, 2),
        "max_safe_ml": round(max_safe_ml, 2),
        "concentration_mg_ml": concentration_mg_ml,
        "max_safe_mg_kg": max_safe_dose_mg_kg,
        "metadata_version": limits_data.get("_metadata", {}).get("version", "1.0")
    }

def evaluate_lidocaine_use(weight, species, concentration_pct, linea_alba_ml, ligamento_ml, peritoneal_ml, piel_ml):
    """
    Evalúa el consumo transoperatorio real contra el límite de toxicidad sistémica.
    """
    limit_info = calculate_lidocaine_limit(weight, species, concentration_pct)
    
    total_ml_used = linea_alba_ml + ligamento_ml + peritoneal_ml + piel_ml
    total_mg_used = total_ml_used * limit_info["concentration_mg_ml"]
    
    percentage_consumed = (total_mg_used / limit_info["max_safe_mg"] * 100.0) if limit_info["max_safe_mg"] > 0 else 0.0
    remaining_ml = max(0.0, limit_info["max_safe_ml"] - total_ml_used)
    
    alerts = []
    status = "SAFE" # SAFE, WARNING, CRITICAL
    
    if total_mg_used > limit_info["max_safe_mg"]:
        alerts.append({
            "type": "lidocaine_toxicity",
            "message": f"Dosis acumulada de lidocaína ({round(total_mg_used, 2)} mg / {round(total_ml_used, 2)} ml) SUPERA el límite máximo seguro calculado de {limit_info['max_safe_mg']} mg ({limit_info['max_safe_ml']} ml). Riesgo severo de toxicidad sistémica y neurotoxicidad en {species}."
        })
        status = "CRITICAL"
    elif percentage_consumed >= 80.0:
        alerts.append({
            "type": "lidocaine_near_limit",
            "message": f"Consumo de lidocaína cercano al límite de seguridad ({round(percentage_consumed, 1)}% consumido). Extremar precauciones."
        })
        status = "WARNING"
        
    return {
        "max_safe_mg": limit_info["max_safe_mg"],
        "max_safe_ml": limit_info["max_safe_ml"],
        "total_ml_used": round(total_ml_used, 2),
        "total_mg_used": round(total_mg_used, 2),
        "percentage_consumed": round(percentage_consumed, 1),
        "remaining_ml": round(remaining_ml, 2),
        "status": status,
        "alerts": alerts
    }
