import math
import json
import pytest
from services.propofol_service import calculate_propofol
from services.pump_service import calculate_pump

# Helper to check numeric sanity
def is_finite_number(value):
    return isinstance(value, (int, float)) and math.isfinite(value)

# Parameter matrix covering the requested scenarios
@pytest.mark.parametrize(
    "weight,species,asa,concentration_pct,target_dose,duration_min,dead_volume,flow_ml_h,primed,primed_with,expected_flow_alarm",
    [
        # 1. Perro pequeño
        (5, "dog", "I", 1, 0.2, 60, 5, 46, "si", "suero", False),
        # 2. Perro mediano
        (15, "dog", "II", 1, 0.2, 60, 5, 1.5, "si", "mezcla", True),
        # 3. Perro grande
        (30, "dog", "III", 2, 0.3, 120, 10, 3, "no", "suero", False),
        # 4. Gato joven
        (4, "cat", "I", 1, 0.15, 30, 2, 1.8, "si", "suero", False),
        # 5. Gato adulto
        (5, "cat", "II", 1, 0.2, 60, 3, 2.5, "si", "mezcla", False),
        # 9. ASA IV
        (20, "dog", "IV", 1, 0.25, 90, 5, 4, "si", "suero", False),
        # 10. ASA V
        (25, "dog", "V", 2, 0.3, 120, 5, 5, "si", "mezcla", False),
        # 11. Propofol 1%
        (10, "dog", "I", 1, 0.2, 60, 5, 46, "si", "suero", False),
        # 12. Propofol 2%
        (10, "dog", "I", 2, 0.2, 60, 5, 46, "si", "suero", False),
        # 13. Duración corta
        (10, "dog", "I", 1, 0.2, 30, 5, 46, "si", "suero", False),
        # 14. Duración larga
        (10, "dog", "I", 1, 0.2, 180, 5, 46, "si", "suero", False),
        # 15. Línea cebada con suero
        (10, "dog", "I", 1, 0.2, 60, 5, 46, "si", "suero", False),
        # 16. Línea cebada con mezcla
        (10, "dog", "I", 1, 0.2, 60, 5, 46, "si", "mezcla", False),
        # 17. Volumen muerto 0 ml
        (10, "dog", "I", 1, 0.2, 60, 0, 46, "si", "suero", False),
        # 18. Volumen muerto alto
        (10, "dog", "I", 1, 0.2, 60, 50, 46, "si", "suero", False),
        # 19. Flujo bajo (<2 ml/h)
        (10, "dog", "I", 1, 0.2, 60, 5, 1.5, "si", "suero", True),
        # 20. Flujo normal
        (10, "dog", "I", 1, 0.2, 60, 5, 5, "si", "suero", False),
        # 21. Flujo elevado
        (10, "dog", "I", 1, 0.2, 60, 5, 10, "si", "suero", False),
    ]
)
def test_core_calculations(
    weight, species, asa, concentration_pct, target_dose, duration_min,
    dead_volume, flow_ml_h, primed, primed_with, expected_flow_alarm
):
    # Calculate propofol preparation
    prop_res = calculate_propofol(
        weight=weight,
        duration_min=duration_min,
        target_dose=target_dose,
        concentration_pct=concentration_pct,
        saline_ml=dead_volume,  # Using dead_volume as diluent for simplicity
        species=species,
        asa=asa,
    )

    # Verify numeric fields are finite and non-negative
    for key in [
        "mg_per_min", "mg_per_hour", "mg_total",
        "ml_propofol", "ml_saline", "volume_final",
        "final_concentration_mg_ml", "flow_ml_h", "vtbi_ml",
    ]:
        assert is_finite_number(prop_res[key]), f"Propofol result {key} is not a finite number"
        assert prop_res[key] >= 0, f"Propofol result {key} is negative"

    # Run pump calculations
    pump_res = calculate_pump(
        volume_final=prop_res["volume_final"],
        flow_ml_h=flow_ml_h,
        vtbi_ml=prop_res["vtbi_ml"],
        time_min=duration_min,
        dead_volume_ml=dead_volume,
        line_primed=primed,
        primed_with=primed_with,
    )

    # Verify pump fields
    for key in ["volume_final", "flow_ml_h", "vtbi_ml", "time_min", "priming_delay_min"]:
        assert is_finite_number(pump_res[key]), f"Pump result {key} is not a finite number"
        assert pump_res[key] >= 0, f"Pump result {key} is negative"

    # Flow alarm check
    assert pump_res["flow_alarm"] == expected_flow_alarm

    # Safety message should be a non-empty string
    assert isinstance(pump_res["safety_message"], str) and pump_res["safety_message"]

    # If line is primed with mixture, warning must contain specific text
    if primed == "si" and primed_with == "mezcla":
        assert "Cebado con mezcla" in pump_res["priming_warning"]
    else:
        assert "mezcla" not in pump_res["priming_warning"].lower()
