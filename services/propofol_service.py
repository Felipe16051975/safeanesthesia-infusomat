import os
import json

# RUTA ABSOLUTA PARA ACCEDER A CONFIGURACIONES DESDE EL SERVICIO
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'propofol_limits.json')

def load_limits():
    """Carga los límites dinámicamente desde el JSON configurado por el veterinario."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        # Fallback de emergencia si no se encuentra o hay error en el JSON
        return {
            "limits": {
                "dog": {
                    "minDose": 0.1,
                    "maxDose": 0.4,
                    "warningThreshold": 0.45,
                    "criticalThreshold": 0.6
                },
                "cat": {
                    "minDose": 0.1,
                    "maxDose": 0.3,
                    "warningThreshold": 0.35,
                    "criticalThreshold": 0.5
                }
            }
        }

def calculate_propofol(weight, target_dose, duration_min, species, propofol_pct, asa_class):
    """
    Realiza los cálculos de mantenimiento farmacológico de propofol.
    
    Parámetros:
      - weight: Peso en kg (>0)
      - target_dose: Dosis objetivo en mg/kg/min
      - duration_min: Duración estimada de mantenimiento en minutos
      - species: 'dog' o 'cat'
      - propofol_pct: '1%' o '2%'
      - asa_class: 'I', 'II', 'III', 'IV', 'V'
    
    Retorna:
      - Un diccionario con mg/min, mg/h, mg totales, ml a extraer, alertas y observaciones.
    """
    if weight <= 0:
        raise ValueError("El peso debe ser mayor a 0 kg.")
    
    # Carga de límites
    limits_data = load_limits()
    limits = limits_data["limits"].get(species, limits_data["limits"]["dog"])
    
    # Conversión de concentración
    concentration = 10.0 if propofol_pct == '1%' else 20.0 # 10 mg/ml o 20 mg/ml
    
    # Fórmulas de dosificación
    mg_min = weight * target_dose
    mg_h = mg_min * 60.0
    total_mg = mg_h * (duration_min / 60.0)
    required_ml = total_mg / concentration
    
    # Inicialización de alertas clínicas
    alerts = []
    alert_level = "SAFE" # SAFE, WARNING, CRITICAL
    
    # 1. Alerta por dosis objetivo contra los rangos JSON
    if target_dose > limits["criticalThreshold"]:
        alerts.append({
            "type": "dose_critical",
            "message": f"Dosis objetivo crítica ({target_dose} mg/kg/min) sobrepasa el límite crítico de {limits['criticalThreshold']} mg/kg/min definido para la especie {species}. Se requiere justificación clínica activa."
        })
        alert_level = "CRITICAL"
    elif target_dose > limits["warningThreshold"]:
        alerts.append({
            "type": "dose_warning",
            "message": f"Dosis objetivo elevada ({target_dose} mg/kg/min) sobrepasa el límite de advertencia de {limits['warningThreshold']} mg/kg/min."
        })
        if alert_level != "CRITICAL":
            alert_level = "WARNING"
            
    # 2. Alertas basadas en la clasificación ASA del paciente
    if asa_class in ['IV', 'V']:
        alerts.append({
            "type": "asa_critical",
            "message": f"Paciente clasificado como ASA {asa_class} (Alto Riesgo). Requiere evaluación anestésica avanzada, monitorización intensiva y soporte cardiovascular y ventilatorio activo."
        })
        alert_level = "CRITICAL"
    elif asa_class == 'III':
        alerts.append({
            "type": "asa_warning",
            "message": "Paciente clasificado como ASA III. Presenta enfermedad sistémica moderada-grave. Monitorear de forma estricta."
        })
        if alert_level != "CRITICAL":
            alert_level = "WARNING"
            
    # 3. Alerta por especie (Gato) - saturación fenólica
    if species == 'cat':
        alerts.append({
            "type": "cat_phenolic_warning",
            "message": "Los gatos presentan un metabolismo fenólico retardado. El uso repetido o prolongado de propofol puede dar origen a cuerpos de Heinz y recuperaciones prolongadas."
        })
        if duration_min > 60:
            alerts.append({
                "type": "cat_duration_critical",
                "message": f"La infusión supera los 60 minutos en gato ({duration_min} min). Riesgo elevado de toxicidad eritrocitaria y despertar retardado. Se sugiere evaluar protocolos PIVA multimodales."
            })
            alert_level = "CRITICAL"
        elif alert_level == "SAFE":
            alert_level = "WARNING"
            
    return {
        "mg_min": round(mg_min, 3),
        "mg_h": round(mg_h, 2),
        "total_mg": round(total_mg, 2),
        "required_ml": round(required_ml, 2),
        "concentration_mg_ml": concentration,
        "alert_level": alert_level,
        "alerts": alerts,
        "metadata_version": limits_data.get("_metadata", {}).get("version", "1.0"),
        "metadata_reviewed_by": limits_data.get("_metadata", {}).get("reviewed_by", "Desconocido")
    }
