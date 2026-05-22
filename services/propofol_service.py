import json
from pathlib import Path
from typing import Dict, Any


def load_limits() -> Dict[str, Any]:
    """Read clinical limits from config/clinical_limits.json."""
    config_path = Path(__file__).parent.parent / "config" / "clinical_limits.json"

    if not config_path.is_file():
        return {
            "propofol": {
                "dog": {
                    "minDose": 0.0,
                    "maxDose": 0.4,
                    "warningThreshold": 0.45,
                    "criticalThreshold": 0.6,
                },
                "cat": {
                    "minDose": 0.0,
                    "maxDose": 0.3,
                    "warningThreshold": 0.35,
                    "criticalThreshold": 0.5,
                },
            }
        }

    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)


def classify_safety(species: str, dose_mg_kg_min: float, limits: Dict[str, Any]) -> str:
    """Classify dose as SAFE, WARNING, or CRITICAL."""
    species_key = (species or "dog").lower()
    species_limits = limits.get("propofol", {}).get(species_key, {})

    max_dose = species_limits.get("maxDose")
    warning = species_limits.get("warningThreshold")
    critical = species_limits.get("criticalThreshold")

    if max_dose is None or warning is None or critical is None:
        return "SAFE"

    if dose_mg_kg_min > critical:
        return "CRITICAL"

    if dose_mg_kg_min > max_dose or dose_mg_kg_min > warning:
        return "WARNING"

    return "SAFE"


def calculate_propofol(
    weight: float,
    duration_min: float,
    target_dose: float,
    concentration_pct: float,
    saline_ml: float,
    species: str = "dog",
    asa: str = "I",
) -> Dict[str, Any]:
    """Calculate complete propofol preparation for volumetric Infusomat use.

    Stages:
    A. mg/min
    B. mg/h
    C. mg total
    D. ml commercial propofol
    E. ml NaCl selected by user
    F. final mixture volume
    G. final concentration mg/ml
    H. FLOW ml/h
    I. VTBI ml
    J. TIME min
    """

    if weight <= 0:
        raise ValueError("El peso debe ser mayor a 0 kg.")

    if duration_min <= 0:
        raise ValueError("La duración debe ser mayor a 0 minutos.")

    if target_dose <= 0:
        raise ValueError("La dosis objetivo debe ser mayor a 0.")

    if concentration_pct not in (1, 2, 1.0, 2.0):
        raise ValueError("La concentración de propofol debe ser 1% o 2%.")

    if saline_ml < 0:
        raise ValueError("El volumen de suero no puede ser negativo.")

    limits = load_limits()

    commercial_concentration_mg_ml = 10 * float(concentration_pct)

    mg_per_min = weight * target_dose
    mg_per_hour = mg_per_min * 60
    mg_total = mg_per_min * duration_min

    ml_propofol = mg_total / commercial_concentration_mg_ml

    volume_final = ml_propofol + saline_ml
    final_concentration = mg_total / volume_final if volume_final > 0 else 0

    flow_ml_h = volume_final / (duration_min / 60)
    vtbi_ml = volume_final

    safety_level = classify_safety(species, target_dose, limits)

    return {
        "mg_per_min": round(mg_per_min, 3),
        "mg_per_hour": round(mg_per_hour, 3),
        "mg_total": round(mg_total, 3),
        "commercial_concentration_mg_ml": commercial_concentration_mg_ml,
        "ml_propofol": round(ml_propofol, 3),
        "ml_saline": round(saline_ml, 3),
        "volume_final": round(volume_final, 3),
        "final_concentration_mg_ml": round(final_concentration, 4),
        "flow_ml_h": round(flow_ml_h, 3),
        "vtbi_ml": round(vtbi_ml, 3),
        "time_min": duration_min,
        "safety_level": safety_level,
        "concentration_pct": concentration_pct,
        "species": species,
        "asa": asa,
    }

