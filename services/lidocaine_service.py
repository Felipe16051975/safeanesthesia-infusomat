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
    """Return lidocaine meta-config for the UI (concentrations, sites, limits, classification)."""
    cfg = load_limits().get('lidocaine', {})
    return {
        'concentrations':  cfg.get('concentrations', []),
        'sites':           cfg.get('sites', []),
        'max_mg_per_kg':   cfg.get('max_mg_per_kg', {}),
        'classification':  cfg.get('classification', {}),
    }


def calculate_lidocaine(weight: float, species: str, target_limit_dose: float,
                        concentration_mg_ml: float,
                        linea_alba_ml: float = 0.0,
                        ligamento_ml: float = 0.0,
                        peritoneal_ml: float = 0.0,
                        piel_ml: float = 0.0,
                        site: str = None) -> dict:
    """Calculate local lidocaine balance and safety classification.

    Parameters
    ----------
    weight              : patient weight (kg)
    species             : 'dog' | 'cat' (or Spanish equivalents)
    target_limit_dose   : user-provided dose limit (mg/kg)
    concentration_mg_ml : lidocaine solution concentration (mg/ml)
    linea_alba_ml       : volume injected at linea alba (ml)
    ligamento_ml        : volume injected at ovarian ligament (ml)
    peritoneal_ml       : volume injected peritoneally (ml)
    piel_ml             : volume injected at skin/subcutaneous (ml)
    site                : free-text anatomical site label (optional)

    Returns
    -------
    dict with keys:
        max_allowed_mg, max_allowed_ml,
        total_injected_ml, total_injected_mg,
        accumulated_mg (alias of total_injected_mg),
        remaining_mg, remaining_ml,
        pct_of_max, status, site, alerts, warning_label
    """
    limits_data = load_limits()
    lido_cfg = limits_data.get('lidocaine', {})

    # Classification thresholds (percentage of max allowed)
    classification_cfg = lido_cfg.get('classification', {})
    safe_pct     = classification_cfg.get('safe_percent', 70)
    warning_pct  = classification_cfg.get('warning_percent', 90)
    critical_pct = classification_cfg.get('critical_percent', 100)

    # Toxic limit per species
    is_cat = species.lower() in ['cat', 'gato', 'felino']
    species_key = 'cat' if is_cat else 'dog'
    toxic_limits  = lido_cfg.get('max_mg_per_kg', {})
    species_toxic = toxic_limits.get(species_key, 0)

    # Maximum allowed dose (mg)
    max_allowed_mg = weight * target_limit_dose
    max_allowed_ml = max_allowed_mg / concentration_mg_ml if concentration_mg_ml > 0 else 0.0

    # Total injected
    total_injected_ml = linea_alba_ml + ligamento_ml + peritoneal_ml + piel_ml
    total_injected_mg = total_injected_ml * concentration_mg_ml

    remaining_mg = max_allowed_mg - total_injected_mg
    remaining_ml = remaining_mg / concentration_mg_ml if concentration_mg_ml > 0 else 0.0

    pct_of_max = (total_injected_mg / max_allowed_mg * 100.0) if max_allowed_mg > 0 else 0.0

    alerts = []
    status = 'SAFE'

    # Validate that user-provided limit doesn't exceed species toxic limit
    if target_limit_dose > species_toxic and species_toxic > 0:
        status = 'WARNING'
        alerts.append(
            f"ADVERTENCIA: La dosis límite ingresada ({target_limit_dose} mg/kg) supera "
            f"el límite tóxico recomendado para {species_key} ({species_toxic} mg/kg)."
        )

    # Classification by percentage
    if pct_of_max >= critical_pct:
        status = 'CRITICAL'
        alerts.append(
            f"PELIGRO DE TOXICIDAD SISTÉMICA: {round(total_injected_mg, 2)} mg administrados "
            f"representan el {round(pct_of_max, 1)}% de la dosis máxima segura."
        )
    elif pct_of_max >= warning_pct and status != 'CRITICAL':
        status = 'WARNING'
        alerts.append(
            f"ADVERTENCIA: {round(total_injected_mg, 2)} mg administrados representan el "
            f"{round(pct_of_max, 1)}% de la dosis máxima. Cerca del límite."
        )

    warning_label = (
        "No sobrepasar dosis total acumulada. Considerar toda lidocaína usada durante el "
        "procedimiento, incluyendo intubación, infiltración, splash block o instilación."
    )

    return {
        'max_allowed_mg':    round(max_allowed_mg, 2),
        'max_allowed_ml':    round(max_allowed_ml, 2),
        'total_injected_ml': round(total_injected_ml, 2),
        'total_injected_mg': round(total_injected_mg, 2),
        'accumulated_mg':    round(total_injected_mg, 2),   # alias for front-end
        'remaining_mg':      round(remaining_mg, 2),
        'remaining_ml':      round(remaining_ml, 2),
        'pct_of_max':        round(pct_of_max, 1),
        'status':            status,
        'site':              site,
        'alerts':            alerts,
        'warning_label':     warning_label,
    }
