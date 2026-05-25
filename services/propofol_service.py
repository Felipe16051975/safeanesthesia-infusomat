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

def calculate_propofol(weight, target_dose, duration_min, species, propofol_pct, asa_class,
                       anesthesia_mode='propofol_solo',
                       ketamine_concentration=50.0,
                       ketamine_target_dose=0.1,
                       use_ratio_1_2=False,
                       diluent_volume=40.0,
                       container_type=None,
                       propofol_dose_unit='mg/kg/min',
                       ketamine_dose_unit='mg/kg/min'):
    """
    Realiza los cálculos de mantenimiento farmacológico de propofol y ketamina (Pre-Q).
    """
    if weight <= 0:
        raise ValueError("El peso debe ser mayor a 0 kg.")
    if duration_min <= 0:
        raise ValueError("La duración estimada debe ser mayor a 0 minutos.")
    if target_dose < 0:
        raise ValueError("La dosis de propofol no puede ser negativa.")
    if ketamine_target_dose < 0:
        raise ValueError("La dosis de ketamina no puede ser negativa.")
    if diluent_volume < 0:
        raise ValueError("El volumen del diluyente no puede ser negativo.")

    # Helper para conversión a mg/kg/min
    def convert_to_mg_kg_min(val, unit):
        if unit == 'mg/kg/h':
            return val / 60.0
        elif unit == 'mcg/kg/min':
            return val / 1000.0
        return val

    # Carga de límites para propofol (retrocompatibilidad)
    limits_data = load_limits()
    limits = limits_data["limits"].get(species, limits_data["limits"]["dog"])
    
    # Conversión de dosis
    p_dose_converted = convert_to_mg_kg_min(target_dose, propofol_dose_unit)
    
    if anesthesia_mode == 'propofol_ketamine_mixture' and use_ratio_1_2:
        k_dose_converted = p_dose_converted / 2.0
    else:
        k_dose_converted = convert_to_mg_kg_min(ketamine_target_dose, ketamine_dose_unit)

    # Conversión de concentración comercial propofol
    concentration = 10.0 if propofol_pct == '2%' or propofol_pct == 20.0 or propofol_pct == '20' else 10.0
    if propofol_pct in ['2%', '2', 2, 2.0, 20.0, '20']:
        concentration = 20.0
    else:
        concentration = 10.0
    
    # Fórmulas de dosificación - Propofol
    mg_min = weight * p_dose_converted
    mg_h = mg_min * 60.0
    total_mg = mg_h * (duration_min / 60.0)
    required_ml = total_mg / concentration
    
    # Fórmulas de dosificación - Ketamina
    k_required_ml = 0.0
    k_total_mg = 0.0
    k_mg_min = 0.0
    k_mg_h = 0.0
    if anesthesia_mode == 'propofol_ketamine_mixture':
        k_mg_min = weight * k_dose_converted
        k_mg_h = k_mg_min * 60.0
        k_total_mg = k_mg_h * (duration_min / 60.0)
        if ketamine_concentration > 0:
            k_required_ml = k_total_mg / ketamine_concentration

    # Volumen final
    if anesthesia_mode == 'propofol_ketamine_mixture':
        V_final = required_ml + k_required_ml + diluent_volume
    else:
        V_final = required_ml + diluent_volume

    # Concentraciones finales
    final_propofol_conc = total_mg / V_final if V_final > 0 else 0.0
    final_ketamine_conc = k_total_mg / V_final if (V_final > 0 and anesthesia_mode == 'propofol_ketamine_mixture') else 0.0

    # Verificación estricta de dilución (V1C1 = V2C2 / CONCENTRACIÓN FINAL)
    flow_ml_h = V_final / (duration_min / 60.0) if duration_min > 0 else 0.0
    
    # Propofol entregado
    delivered_propofol_mg_h = flow_ml_h * final_propofol_conc
    delivered_propofol_mg_kg_min = (delivered_propofol_mg_h / weight) / 60.0 if weight > 0 else 0.0
    
    # Ketamina entregada
    delivered_ketamine_mg_h = flow_ml_h * final_ketamine_conc
    delivered_ketamine_mg_kg_min = (delivered_ketamine_mg_h / weight) / 60.0 if weight > 0 else 0.0

    # Validación de tolerancia (< 1%)
    if p_dose_converted > 0 and abs(delivered_propofol_mg_kg_min - p_dose_converted) > (p_dose_converted * 0.01):
        raise ValueError(f"Error crítico de dilución: Propofol entregado ({delivered_propofol_mg_kg_min:.4f}) difiere del objetivo ({p_dose_converted:.4f}).")
        
    if anesthesia_mode == 'propofol_ketamine_mixture' and k_dose_converted > 0:
        if abs(delivered_ketamine_mg_kg_min - k_dose_converted) > (k_dose_converted * 0.01):
            raise ValueError(f"Error crítico de dilución: Ketamina entregada ({delivered_ketamine_mg_kg_min:.4f}) difiere del objetivo ({k_dose_converted:.4f}).")

    # Sugerencia de contenedor
    if V_final <= 20.0:
        suggested_container = 'jeringa_20_ml'
    elif V_final <= 50.0:
        suggested_container = 'jeringa_50_ml'
    else:
        suggested_container = 'bolsa_100_ml'

    # Volume Guard
    volume_guard_message = ""
    if V_final <= 50.0:
        volume_guard_status = 'SAFE'
    elif V_final <= 100.0:
        volume_guard_status = 'WARNING'
        volume_guard_message = "Verifique que el volumen total sea apropiado para el tamaño del paciente."
    else:
        volume_guard_status = 'BLOCKED'
        volume_guard_message = "Las mezclas anestésicas superiores a 100 ml no están permitidas."

    # Validación fisiológica secundaria (informativa)
    ml_kg_day = 60.0 if species == 'dog' else 50.0
    maint_h = (ml_kg_day * weight) / 24.0
    maint_periodo = maint_h * (duration_min / 60.0)
    pct_maint_used = (V_final / maint_periodo) * 100.0 if maint_periodo > 0 else 0.0
    maintenance_info_text = f"Esta mezcla equivale al {round(pct_maint_used, 1)}% de la mantención estimada durante el tiempo quirúrgico."

    # Inicialización de alertas clínicas (retrocompatibilidad)
    alerts = []
    alert_level = "SAFE" # SAFE, WARNING, CRITICAL
    
    # 1. Alerta por dosis objetivo contra los rangos JSON (usar dosis convertida)
    if p_dose_converted > limits["criticalThreshold"]:
        alerts.append({
            "type": "dose_critical",
            "message": f"Dosis objetivo crítica ({round(p_dose_converted, 3)} mg/kg/min) sobrepasa el límite crítico de {limits['criticalThreshold']} mg/kg/min definido para la especie {species}. Se requiere justificación clínica activa."
        })
        alert_level = "CRITICAL"
    elif p_dose_converted > limits["warningThreshold"]:
        alerts.append({
            "type": "dose_warning",
            "message": f"Dosis objetivo elevada ({round(p_dose_converted, 3)} mg/kg/min) sobrepasa el límite de advertencia de {limits['warningThreshold']} mg/kg/min."
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
            "message": "Los gatos presentan un metabolism fenólico retardado. El uso repetido o prolongado de propofol puede dar origen a cuerpos de Heinz y recuperaciones prolongadas."
        })
        if duration_min > 60:
            alerts.append({
                "type": "cat_duration_critical",
                "message": f"La infusión supera los 60 minutos en gato ({duration_min} min). Riesgo elevado de toxicidad eritrocitaria y despertar retardado. Se sugiere evaluar protocolos PIVA multimodales."
            })
            alert_level = "CRITICAL"
        elif alert_level == "SAFE":
            alert_level = "WARNING"

    # Advertencias de Ketofol y duración
    ketofol_warnings = []
    if anesthesia_mode == 'propofol_ketamine_mixture':
        ketofol_warnings.append(
            "Precaución clínica: la mezcla de propofol con ketamina puede alterar la estabilidad de la emulsión. "
            "Prepare la mezcla inmediatamente antes de la infusión, úsela dentro de un plazo corto y verifique visualmente homogeneidad antes de conectar la bomba."
        )
        if duration_min > 90:
            ketofol_warnings.append(
                "Infusiones prolongadas con ketamina pueden asociarse a recuperación más prolongada o agitada."
            )

    return {
        "mg_min": round(mg_min, 3),
        "mg_h": round(mg_h, 2),
        "total_mg": round(total_mg, 2),
        "required_ml": round(required_ml, 2),
        "concentration_mg_ml": concentration,
        "alert_level": alert_level,
        "alerts": alerts,
        "metadata_version": limits_data.get("_metadata", {}).get("version", "1.0"),
        "metadata_reviewed_by": limits_data.get("_metadata", {}).get("reviewed_by", "Desconocido"),
        
        # Nuevos campos clínicos
        "anesthesia_mode": anesthesia_mode,
        "ketamine_total_mg": round(k_total_mg, 2),
        "ketamine_required_ml": round(k_required_ml, 2),
        "ketamine_concentration_mg_ml": ketamine_concentration,
        "diluent_volume": diluent_volume,
        "final_volume": round(V_final, 2),
        "final_propofol_concentration": round(final_propofol_conc, 4),
        "final_ketamine_concentration": round(final_ketamine_conc, 4),
        "target_propofol_mg_kg_min": round(p_dose_converted, 4),
        "delivered_propofol_mg_kg_min": round(delivered_propofol_mg_kg_min, 4),
        "target_ketamine_mg_kg_min": round(k_dose_converted, 4) if anesthesia_mode == 'propofol_ketamine_mixture' else 0.0,
        "delivered_ketamine_mg_kg_min": round(delivered_ketamine_mg_kg_min, 4) if anesthesia_mode == 'propofol_ketamine_mixture' else 0.0,
        "flow_ml_h": round(flow_ml_h, 2),
        "suggested_container": suggested_container,
        "selected_container": container_type if container_type else suggested_container,
        "volume_guard_status": volume_guard_status,
        "volume_guard_message": volume_guard_message,
        "maintenance_surgical_estimated": round(maint_periodo, 2),
        "pct_maintenance_used": round(pct_maint_used, 1),
        "maintenance_info_text": maintenance_info_text,
        "ketofol_warnings": ketofol_warnings
    }
