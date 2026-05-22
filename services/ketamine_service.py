import os
import json

def load_limits():
    """Load clinical limits configuration from JSON file."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, 'config', 'clinical_limits.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def get_meta():
    """Return ketamine meta-config for the UI (concentrations, reasons, limits)."""
    cfg = load_limits().get('ketamine', {})
    return {
        'concentrations': cfg.get('concentrations', []),
        'reasons':        cfg.get('reasons', []),
        'limits':         cfg.get('limits', {}),
    }


def calculate_ketamine(weight: float, target_dose: float, concentration_mg_ml: float,
                       species: str = 'dog', reason: str = None,
                       accumulated_mg: float = 0.0) -> dict:
    """Calculate ketamine bolus, classification and running accumulation.

    Parameters
    ----------
    weight              : patient weight in kg
    target_dose         : desired dose in mg/kg
    concentration_mg_ml : ketamine solution concentration (mg/ml)
    species             : 'dog' | 'cat'
    reason              : clinical reason for the bolus (free text)
    accumulated_mg      : total ketamine already given during this procedure (mg)

    Returns
    -------
    dict with keys:
        bolus_mg, bolus_ml, concentration_mg_ml,
        accumulated_mg, new_accumulated_mg, reinforcement_index,
        classification, reason, alerts, warning
    """
    limits = load_limits().get('ketamine', {})

    # Species mapping (Spanish or English)
    is_cat = species.lower() in ['cat', 'gato', 'felino']
    species_key = 'cat' if is_cat else 'dog'
    species_limits = limits.get('limits', {}).get(species_key, {})
    safe_mg     = species_limits.get('safe', 2)
    warning_mg  = species_limits.get('warning', 5)
    critical_mg = species_limits.get('critical', 10)

    bolus_mg = round(weight * target_dose, 4)
    bolus_ml = round(bolus_mg / concentration_mg_ml, 4) if concentration_mg_ml > 0 else 0.0

    new_accumulated_mg = round(accumulated_mg + bolus_mg, 4)

    # reinforcement_index: how many safe-dose equivalents have been given so far
    reinforcement_index = round(new_accumulated_mg / safe_mg, 2) if safe_mg > 0 else 0.0

    alerts = []
    classification = 'SAFE'

    if bolus_mg >= critical_mg:
        classification = 'CRITICAL'
        alerts.append(
            f"ADVERTENCIA CRÍTICA: bolo {bolus_mg:.2f} mg supera el límite crítico "
            f"({critical_mg} mg) para {species_key}."
        )
    elif bolus_mg >= warning_mg:
        classification = 'WARNING'
        alerts.append(
            f"ADVERTENCIA: bolo {bolus_mg:.2f} mg supera el límite de advertencia "
            f"({warning_mg} mg) para {species_key}."
        )
    elif new_accumulated_mg >= warning_mg:
        classification = 'WARNING'
        alerts.append(
            f"ADVERTENCIA: acumulado total {new_accumulated_mg:.2f} mg supera el límite "
            f"de advertencia ({warning_mg} mg) para {species_key}."
        )

    warning_text = (
        "Administrar sólo bajo criterio veterinario, según monitorización y estímulo quirúrgico previsto. "
        "Esta sección sirve para momentos como tracción ovárica, manipulación visceral, "
        "respuesta simpática o movimiento intraoperatorio."
    )

    return {
        'bolus_mg':             round(bolus_mg, 2),
        'bolus_ml':             round(bolus_ml, 4),
        'concentration_mg_ml':  concentration_mg_ml,
        'accumulated_mg':       round(accumulated_mg, 2),
        'new_accumulated_mg':   round(new_accumulated_mg, 2),
        'reinforcement_index':  reinforcement_index,
        'classification':       classification,
        'reason':               reason,
        'alerts':               alerts,
        'warning':              warning_text,
    }
