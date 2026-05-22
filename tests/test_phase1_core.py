import math
# pyrefly: ignore [missing-import]
import pytest
from services.propofol_service import calculate_propofol, load_limits
from services.pump_service import calculate_pump

# Helper for approximate equality
def approx(a, b, tol=1e-3):
    return abs(a - b) <= tol

# 1. Standard feline calculation
def test_feline_standard():
    weight = 5.0
    duration_min = 60
    target_dose = 0.2
    concentration_pct = 1
    saline_ml = 40.0
    # Propofol calculation
    prop = calculate_propofol(
        weight=weight,
        duration_min=duration_min,
        target_dose=target_dose,
        concentration_pct=concentration_pct,
        saline_ml=saline_ml,
        species='cat',
        asa='I',
    )
    assert prop['mg_per_min'] == pytest.approx(1.0)
    assert prop['mg_per_hour'] == pytest.approx(60.0)
    assert prop['mg_total'] == pytest.approx(60.0)
    assert prop['ml_propofol'] == pytest.approx(6.0)
    assert prop['volume_final'] == pytest.approx(46.0)
    assert approx(prop['final_concentration_mg_ml'], 1.3043478)
    assert prop['flow_ml_h'] == pytest.approx(46.0)
    assert prop['vtbi_ml'] == pytest.approx(46.0)
    assert prop['time_min'] == 60
    # Pump calculation – primed with saline, dead volume 5 ml, flow 46
    pump = calculate_pump(
        volume_final=prop['volume_final'],
        flow_ml_h=prop['flow_ml_h'],
        vtbi_ml=prop['vtbi_ml'],
        time_min=prop['time_min'],
        dead_volume_ml=5.0,
        line_primed='si',
        primed_with='suero',
    )
    assert pump['priming_delay_min'] == pytest.approx(6.521739130434783, rel=1e-3)
    assert pump['flow_alarm'] is False
    assert "Cebado con suero" in pump['priming_warning']

# 2. Propofol 2% – volume of propofol should be half of 1% case
def test_propofol_2percent_volume():
    prop1 = calculate_propofol(
        weight=5, duration_min=60, target_dose=0.2,
        concentration_pct=1, saline_ml=40, species='cat', asa='I')
    prop2 = calculate_propofol(
        weight=5, duration_min=60, target_dose=0.2,
        concentration_pct=2, saline_ml=40, species='cat', asa='I')
    # 2% concentration doubles mg/ml, so ml_propofol should be half
    assert prop2['ml_propofol'] == pytest.approx(prop1['ml_propofol'] / 2)

# 3. Primed with saline – priming delay calculation
def test_priming_delay_saline():
    prop = calculate_propofol(
        weight=5, duration_min=60, target_dose=0.2,
        concentration_pct=1, saline_ml=40, species='cat', asa='I')
    pump = calculate_pump(
        volume_final=prop['volume_final'],
        flow_ml_h=46,
        vtbi_ml=prop['vtbi_ml'],
        time_min=prop['time_min'],
        dead_volume_ml=5,
        line_primed='si',
        primed_with='suero',
    )
    assert pump['priming_delay_min'] == pytest.approx(6.521739130434783, rel=1e-3)
    assert "Cebado con suero" in pump['priming_warning']

# 4. Primed with mixture – no delay, warning about flush
def test_priming_mixture_warning():
    prop = calculate_propofol(
        weight=5, duration_min=60, target_dose=0.2,
        concentration_pct=1, saline_ml=40, species='cat', asa='I')
    pump = calculate_pump(
        volume_final=prop['volume_final'],
        flow_ml_h=46,
        vtbi_ml=prop['vtbi_ml'],
        time_min=prop['time_min'],
        dead_volume_ml=5,
        line_primed='si',
        primed_with='mezcla',
    )
    assert pump['priming_delay_min'] == 0
    assert "Cebado con mezcla" in pump['priming_warning']

# 5. Invalid inputs – should raise ValueError
@pytest.mark.parametrize("func,kwargs", [
    (calculate_propofol, {"weight":0, "duration_min":60, "target_dose":0.2, "concentration_pct":1, "saline_ml":40, "species":"cat", "asa":"I"}),
    (calculate_propofol, {"weight":5, "duration_min":0, "target_dose":0.2, "concentration_pct":1, "saline_ml":40, "species":"cat", "asa":"I"}),
    (calculate_propofol, {"weight":5, "duration_min":60, "target_dose":0, "concentration_pct":1, "saline_ml":40, "species":"cat", "asa":"I"}),
    (calculate_propofol, {"weight":5, "duration_min":60, "target_dose":0.2, "concentration_pct":3, "saline_ml":40, "species":"cat", "asa":"I"}),
    (calculate_propofol, {"weight":5, "duration_min":60, "target_dose":0.2, "concentration_pct":1, "saline_ml":-5, "species":"cat", "asa":"I"}),
    (calculate_pump, {"volume_final":0, "flow_ml_h":46, "vtbi_ml":0, "time_min":60, "dead_volume_ml":5, "line_primed":"si", "primed_with":"suero"}),
    (calculate_pump, {"volume_final":46, "flow_ml_h":-1, "vtbi_ml":46, "time_min":60, "dead_volume_ml":5, "line_primed":"si", "primed_with":"suero"}),
    (calculate_pump, {"volume_final":46, "flow_ml_h":46, "vtbi_ml":0, "time_min":-10, "dead_volume_ml":5, "line_primed":"si", "primed_with":"suero"}),
    (calculate_pump, {"volume_final":46, "flow_ml_h":46, "vtbi_ml":46, "time_min":60, "dead_volume_ml":-1, "line_primed":"si", "primed_with":"suero"}),
])
def test_invalid_inputs(func, kwargs):
    with pytest.raises(ValueError):
        func(**kwargs)

# 6. Safety level classifications – using limits config
def test_safety_levels():
    limits = load_limits()
    # SAFE case – dose below max
    safe = calculate_propofol(
        weight=5, duration_min=60, target_dose=0.1,
        concentration_pct=1, saline_ml=40, species='dog', asa='I')
    assert safe['safety_level'] == 'SAFE'
    # WARNING case – above max but below warning threshold (using config values)
    warn = calculate_propofol(
        weight=5, duration_min=60, target_dose=0.45,
        concentration_pct=1, saline_ml=40, species='dog', asa='I')
    # According to limits, warning threshold for dog is 0.45 -> should be WARNING
    assert warn['safety_level'] == 'WARNING'
    # CRITICAL case – above critical threshold
    crit = calculate_propofol(
        weight=5, duration_min=60, target_dose=0.65,
        concentration_pct=1, saline_ml=40, species='dog', asa='I')
    assert crit['safety_level'] == 'CRITICAL'
