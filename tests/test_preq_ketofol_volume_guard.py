"""
test_preq_ketofol_volume_guard.py
==================================
Tests para el módulo Pre-Q Anestesia con soporte Ketofol y Volume Guard.

Cubre:
  - Propofol solo (lógica anterior sin regresiones)
  - Ketofol: Propofol + Ketamina en mezcla
  - Conversión de unidades (mg/kg/h y mcg/kg/min → mg/kg/min)
  - VTBI = volumen final de mezcla
  - Volume Guard: SAFE ≤50 ml / WARNING ≤100 ml / BLOCKED >100 ml
  - Mantención informativa (no bloquea)
  - Sugerencia de contenedor por volumen
"""

import pytest
from services.propofol_service import calculate_propofol


# ── Helpers ────────────────────────────────────────────────────────────────────

BASE = dict(
    weight=10.0,
    target_dose=0.2,          # mg/kg/min
    duration_min=60,
    species='dog',
    propofol_pct='1%',        # 10 mg/ml
    asa_class='I',
    propofol_dose_unit='mg/kg/min',
    ketamine_dose_unit='mg/kg/min',
)


def call(**overrides):
    """Llama calculate_propofol con parámetros base + overrides."""
    params = {**BASE, **overrides}
    return calculate_propofol(**params)


# ══════════════════════════════════════════════════════════════════════════════
# 1. PROPOFOL SOLO – sin regresiones
# ══════════════════════════════════════════════════════════════════════════════

class TestPropofolSolo:

    def test_mg_min_calculation(self):
        """10 kg × 0.2 mg/kg/min = 2.0 mg/min"""
        r = call(anesthesia_mode='propofol_solo', diluent_volume=0.0)
        assert r['mg_min'] == pytest.approx(2.0, abs=1e-3)

    def test_mg_h_calculation(self):
        """2 mg/min × 60 = 120 mg/h"""
        r = call(anesthesia_mode='propofol_solo', diluent_volume=0.0)
        assert r['mg_h'] == pytest.approx(120.0, abs=1e-2)

    def test_total_mg_60_min(self):
        """120 mg/h × 1 h = 120 mg en 60 minutos"""
        r = call(anesthesia_mode='propofol_solo', duration_min=60, diluent_volume=0.0)
        assert r['total_mg'] == pytest.approx(120.0, abs=1e-2)

    def test_required_ml_propofol_10mg_ml(self):
        """120 mg / 10 mg/ml = 12 ml"""
        r = call(anesthesia_mode='propofol_solo', propofol_pct='1%', diluent_volume=0.0)
        assert r['required_ml'] == pytest.approx(12.0, abs=1e-2)

    def test_required_ml_propofol_20mg_ml(self):
        """120 mg / 20 mg/ml = 6 ml"""
        r = call(anesthesia_mode='propofol_solo', propofol_pct='2%', diluent_volume=0.0)
        assert r['required_ml'] == pytest.approx(6.0, abs=1e-2)

    def test_ketamine_fields_zero_in_propofol_solo(self):
        """En modo propofol_solo la ketamina debe ser 0."""
        r = call(anesthesia_mode='propofol_solo', diluent_volume=0.0)
        assert r['ketamine_total_mg'] == pytest.approx(0.0)
        assert r['ketamine_required_ml'] == pytest.approx(0.0)
        assert r['final_ketamine_concentration'] == pytest.approx(0.0)

    def test_final_volume_propofol_solo_with_diluent(self):
        """Vfinal = required_ml + diluent_volume."""
        r = call(anesthesia_mode='propofol_solo', propofol_pct='1%',
                 diluent_volume=20.0, duration_min=60)
        # 12 ml propofol + 20 ml diluente = 32 ml
        assert r['final_volume'] == pytest.approx(32.0, abs=1e-2)

    def test_anesthesia_mode_reflected_in_output(self):
        r = call(anesthesia_mode='propofol_solo', diluent_volume=0.0)
        assert r['anesthesia_mode'] == 'propofol_solo'


# ══════════════════════════════════════════════════════════════════════════════
# 2. CONVERSIÓN DE UNIDADES
# ══════════════════════════════════════════════════════════════════════════════

class TestUnitConversions:

    def test_propofol_mg_kg_h_to_mg_kg_min(self):
        """12 mg/kg/h ÷ 60 = 0.2 mg/kg/min → resultado igual al base."""
        r_base = call(anesthesia_mode='propofol_solo',
                      target_dose=0.2, propofol_dose_unit='mg/kg/min',
                      diluent_volume=0.0)
        r_converted = call(anesthesia_mode='propofol_solo',
                           target_dose=12.0, propofol_dose_unit='mg/kg/h',
                           diluent_volume=0.0)
        assert r_converted['mg_min'] == pytest.approx(r_base['mg_min'], abs=1e-3)
        assert r_converted['total_mg'] == pytest.approx(r_base['total_mg'], abs=1e-2)

    def test_propofol_mcg_kg_min_to_mg_kg_min(self):
        """200 mcg/kg/min ÷ 1000 = 0.2 mg/kg/min → resultado igual al base."""
        r_base = call(anesthesia_mode='propofol_solo',
                      target_dose=0.2, propofol_dose_unit='mg/kg/min',
                      diluent_volume=0.0)
        r_converted = call(anesthesia_mode='propofol_solo',
                           target_dose=200.0, propofol_dose_unit='mcg/kg/min',
                           diluent_volume=0.0)
        assert r_converted['mg_min'] == pytest.approx(r_base['mg_min'], abs=1e-3)
        assert r_converted['total_mg'] == pytest.approx(r_base['total_mg'], abs=1e-2)

    def test_ketamine_mg_kg_h_to_mg_kg_min(self):
        """Ketamina en mg/kg/h debe convertirse correctamente."""
        # 0.1 mg/kg/min == 6 mg/kg/h
        r_min = call(anesthesia_mode='propofol_ketamine_mixture',
                     ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
                     ketamine_concentration=50.0, diluent_volume=0.0)
        r_h = call(anesthesia_mode='propofol_ketamine_mixture',
                   ketamine_target_dose=6.0, ketamine_dose_unit='mg/kg/h',
                   ketamine_concentration=50.0, diluent_volume=0.0)
        assert r_h['ketamine_total_mg'] == pytest.approx(r_min['ketamine_total_mg'], abs=1e-2)

    def test_ketamine_mcg_kg_min_to_mg_kg_min(self):
        """Ketamina en mcg/kg/min debe convertirse correctamente."""
        # 0.1 mg/kg/min == 100 mcg/kg/min
        r_min = call(anesthesia_mode='propofol_ketamine_mixture',
                     ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
                     ketamine_concentration=50.0, diluent_volume=0.0)
        r_mcg = call(anesthesia_mode='propofol_ketamine_mixture',
                     ketamine_target_dose=100.0, ketamine_dose_unit='mcg/kg/min',
                     ketamine_concentration=50.0, diluent_volume=0.0)
        assert r_mcg['ketamine_total_mg'] == pytest.approx(r_min['ketamine_total_mg'], abs=1e-2)


# ══════════════════════════════════════════════════════════════════════════════
# 3. KETOFOL – mezcla en misma jeringa
# ══════════════════════════════════════════════════════════════════════════════

class TestKetofol:

    def test_ketamine_total_mg_calculation(self):
        """
        10 kg × 0.1 mg/kg/min × 60 min/h × 1 h = 60 mg ketamina en 60 min.
        """
        r = call(anesthesia_mode='propofol_ketamine_mixture',
                 ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
                 ketamine_concentration=50.0, diluent_volume=0.0)
        assert r['ketamine_total_mg'] == pytest.approx(60.0, abs=1e-2)

    def test_ketamine_required_ml_calculation(self):
        """60 mg / 50 mg/ml = 1.2 ml ketamina."""
        r = call(anesthesia_mode='propofol_ketamine_mixture',
                 ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
                 ketamine_concentration=50.0, diluent_volume=0.0)
        assert r['ketamine_required_ml'] == pytest.approx(1.2, abs=1e-2)

    def test_final_volume_ketofol(self):
        """Vfinal = ml_propofol + ml_ketamina + diluente."""
        r = call(anesthesia_mode='propofol_ketamine_mixture',
                 propofol_pct='1%',        # 10 mg/ml
                 ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
                 ketamine_concentration=50.0, diluent_volume=10.0)
        # propofol: 120 mg / 10 = 12 ml
        # ketamina:  60 mg / 50 =  1.2 ml
        # diluente:                10.0 ml
        expected = 12.0 + 1.2 + 10.0
        assert r['final_volume'] == pytest.approx(expected, abs=1e-2)

    def test_final_propofol_concentration(self):
        """Concentración final propofol = total_mg_propofol / Vfinal."""
        r = call(anesthesia_mode='propofol_ketamine_mixture',
                 propofol_pct='1%',
                 ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
                 ketamine_concentration=50.0, diluent_volume=10.0)
        expected_conc = r['total_mg'] / r['final_volume']
        assert r['final_propofol_concentration'] == pytest.approx(expected_conc, abs=1e-2)

    def test_final_ketamine_concentration(self):
        """Concentración final ketamina = total_mg_ketamina / Vfinal."""
        r = call(anesthesia_mode='propofol_ketamine_mixture',
                 propofol_pct='1%',
                 ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
                 ketamine_concentration=50.0, diluent_volume=10.0)
        expected_conc = r['ketamine_total_mg'] / r['final_volume']
        assert r['final_ketamine_concentration'] == pytest.approx(expected_conc, abs=1e-2)

    def test_ketofol_mode_reflected_in_output(self):
        r = call(anesthesia_mode='propofol_ketamine_mixture',
                 ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
                 ketamine_concentration=50.0, diluent_volume=0.0)
        assert r['anesthesia_mode'] == 'propofol_ketamine_mixture'

    def test_use_ratio_1_2_auto_ketamine_dose(self):
        """
        Relación 1:2 — ketamina = propofol_dose / 2.
        Con propofol 0.2 mg/kg/min → ketamina 0.1 mg/kg/min.
        """
        r_ratio = call(anesthesia_mode='propofol_ketamine_mixture',
                       target_dose=0.2, propofol_dose_unit='mg/kg/min',
                       use_ratio_1_2=True,
                       ketamine_concentration=50.0, diluent_volume=0.0)
        r_manual = call(anesthesia_mode='propofol_ketamine_mixture',
                        target_dose=0.2, propofol_dose_unit='mg/kg/min',
                        ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
                        use_ratio_1_2=False,
                        ketamine_concentration=50.0, diluent_volume=0.0)
        assert r_ratio['ketamine_total_mg'] == pytest.approx(r_manual['ketamine_total_mg'], abs=1e-2)

    def test_ketofol_warning_present_in_mixture_mode(self):
        """La advertencia de estabilidad de emulsión siempre aparece en modo mezcla."""
        r = call(anesthesia_mode='propofol_ketamine_mixture',
                 ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
                 ketamine_concentration=50.0, diluent_volume=0.0)
        assert len(r['ketofol_warnings']) >= 1
        assert any('emulsión' in w.lower() or 'estabilidad' in w.lower()
                   for w in r['ketofol_warnings'])

    def test_ketofol_duration_warning_over_90_min(self):
        """Infusión > 90 min debe agregar advertencia adicional de duración."""
        r = call(anesthesia_mode='propofol_ketamine_mixture',
                 duration_min=120,
                 ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
                 ketamine_concentration=50.0, diluent_volume=0.0)
        assert len(r['ketofol_warnings']) >= 2

    def test_no_ketofol_warnings_in_propofol_solo(self):
        """Modo propofol_solo NO debe generar advertencias de Ketofol."""
        r = call(anesthesia_mode='propofol_solo', diluent_volume=0.0)
        assert r['ketofol_warnings'] == []


# ══════════════════════════════════════════════════════════════════════════════
# 4. VOLUME GUARD
# ══════════════════════════════════════════════════════════════════════════════

class TestVolumeGuard:

    def test_volume_guard_safe_exactly_50(self):
        """Vfinal exactamente 50 ml → SAFE."""
        r = call(anesthesia_mode='propofol_solo',
                 propofol_pct='1%',   # 10 mg/ml
                 target_dose=0.2, duration_min=60,   # 12 ml propofol
                 diluent_volume=38.0)                # 12 + 38 = 50 ml
        assert r['final_volume'] == pytest.approx(50.0, abs=1e-1)
        assert r['volume_guard_status'] == 'SAFE'
        assert r['volume_guard_message'] == ''

    def test_volume_guard_safe_below_50(self):
        """Vfinal < 50 ml → SAFE."""
        r = call(anesthesia_mode='propofol_solo',
                 propofol_pct='1%', target_dose=0.2, duration_min=60,
                 diluent_volume=20.0)   # 12 + 20 = 32 ml
        assert r['volume_guard_status'] == 'SAFE'

    def test_volume_guard_warning_at_51(self):
        """Vfinal = 51 ml → WARNING."""
        r = call(anesthesia_mode='propofol_solo',
                 propofol_pct='1%', target_dose=0.2, duration_min=60,
                 diluent_volume=39.0)   # 12 + 39 = 51 ml
        assert r['volume_guard_status'] == 'WARNING'
        assert 'volumen' in r['volume_guard_message'].lower()

    def test_volume_guard_warning_at_100(self):
        """Vfinal exactamente 100 ml → WARNING (límite superior)."""
        r = call(anesthesia_mode='propofol_solo',
                 propofol_pct='1%', target_dose=0.2, duration_min=60,
                 diluent_volume=88.0)   # 12 + 88 = 100 ml
        assert r['volume_guard_status'] == 'WARNING'

    def test_volume_guard_blocked_above_100(self):
        """Vfinal > 100 ml → BLOCKED."""
        r = call(anesthesia_mode='propofol_solo',
                 propofol_pct='1%', target_dose=0.2, duration_min=60,
                 diluent_volume=100.0)   # 12 + 100 = 112 ml
        assert r['volume_guard_status'] == 'BLOCKED'
        assert '100' in r['volume_guard_message']

    def test_volume_guard_blocked_message_present(self):
        """BLOCKED tiene mensaje específico."""
        r = call(anesthesia_mode='propofol_solo',
                 propofol_pct='1%', target_dose=0.2, duration_min=60,
                 diluent_volume=200.0)
        assert r['volume_guard_message'] != ''

    def test_volume_guard_does_not_block_on_maintenance_percent(self):
        """
        Un gato de 4 kg con mezcla clínicamente válida de ~35 ml
        NO debe bloquearse aunque supere el 100% de mantención de 1 hora.
        """
        r = calculate_propofol(
            weight=4.0,
            target_dose=0.2,
            duration_min=60,
            species='cat',
            propofol_pct='1%',
            asa_class='I',
            anesthesia_mode='propofol_solo',
            diluent_volume=25.0,   # ~9.6 ml propofol + 25 = ~34.6 ml
            propofol_dose_unit='mg/kg/min',
            ketamine_dose_unit='mg/kg/min',
        )
        # maint quirúrgica 1h gato 4 kg ≈ (50 ml/kg/día × 4 kg)/24 ≈ 8.3 ml
        # 34.6 ml >> 8.3 ml → sin el nuevo VG se bloquearía
        assert r['volume_guard_status'] == 'SAFE'


# ══════════════════════════════════════════════════════════════════════════════
# 5. MANTENCIÓN INFORMATIVA (no bloquea)
# ══════════════════════════════════════════════════════════════════════════════

class TestMaintenanceInformative:

    def test_maintenance_fields_always_present(self):
        """Los campos de mantención siempre deben estar en la respuesta."""
        r = call(anesthesia_mode='propofol_solo', diluent_volume=0.0)
        assert 'maintenance_surgical_estimated' in r
        assert 'pct_maintenance_used' in r
        assert 'maintenance_info_text' in r

    def test_maintenance_info_text_contains_percent(self):
        """El texto informativo debe mencionar el porcentaje."""
        r = call(anesthesia_mode='propofol_solo', diluent_volume=0.0)
        assert '%' in r['maintenance_info_text']

    def test_maintenance_does_not_block_at_200_percent(self):
        """
        Aunque el porcentaje de mantención sea 200%, el Volume Guard
        NO debe activar BLOCKED si Vfinal ≤ 50 ml.
        """
        # Forzamos un escenario de alta relación sin superar 50 ml
        r = call(anesthesia_mode='propofol_solo',
                 weight=1.0,         # 1 kg dog → maint ≈ 2.5 ml/h
                 duration_min=60,
                 target_dose=0.2,    # 0.2 × 1 × 60 = 12 mg; 12/10 = 1.2 ml
                 propofol_pct='1%',
                 diluent_volume=10.0)  # 11.2 ml total → SAFE
        assert r['volume_guard_status'] == 'SAFE'
        # El porcentaje puede ser alto, pero no importa
        assert r['pct_maintenance_used'] > 0

    def test_maintenance_dog_ml_kg_day_60(self):
        """
        Perro: mantención referencia = 60 ml/kg/día.
        Para 10 kg en 60 min: (60 × 10) / 24 × (60/60) = 25 ml.
        """
        r = call(anesthesia_mode='propofol_solo', weight=10.0, duration_min=60,
                 diluent_volume=0.0)
        assert r['maintenance_surgical_estimated'] == pytest.approx(25.0, abs=1e-1)

    def test_maintenance_cat_ml_kg_day_50(self):
        """
        Gato: mantención referencia = 50 ml/kg/día.
        Para 4 kg en 60 min: (50 × 4) / 24 × (60/60) ≈ 8.33 ml.
        """
        r = calculate_propofol(
            weight=4.0, target_dose=0.2, duration_min=60,
            species='cat', propofol_pct='1%', asa_class='I',
            anesthesia_mode='propofol_solo', diluent_volume=0.0,
            propofol_dose_unit='mg/kg/min', ketamine_dose_unit='mg/kg/min',
        )
        assert r['maintenance_surgical_estimated'] == pytest.approx(8.33, abs=0.1)


# ══════════════════════════════════════════════════════════════════════════════
# 6. SUGERENCIA DE CONTENEDOR
# ══════════════════════════════════════════════════════════════════════════════

class TestContainerSuggestion:

    def test_suggests_20ml_syringe_when_volume_le_20(self):
        """Vfinal ≤ 20 ml → jeringa 20 ml."""
        r = call(anesthesia_mode='propofol_solo',
                 propofol_pct='1%', target_dose=0.1, duration_min=30,
                 diluent_volume=0.0)
        # 10 kg × 0.1 × 60 = 60 mg → pero 30 min → 30 mg; 30/10 = 3 ml
        assert r['final_volume'] <= 20.0
        assert r['suggested_container'] == 'jeringa_20_ml'

    def test_suggests_50ml_syringe_when_volume_le_50(self):
        """20 < Vfinal ≤ 50 ml → jeringa 50 ml."""
        r = call(anesthesia_mode='propofol_solo',
                 propofol_pct='1%', target_dose=0.2, duration_min=60,
                 diluent_volume=20.0)  # 12 + 20 = 32 ml
        assert 20.0 < r['final_volume'] <= 50.0
        assert r['suggested_container'] == 'jeringa_50_ml'

    def test_suggests_100ml_bag_when_volume_over_50(self):
        """Vfinal > 50 ml → bolsa 100 ml."""
        r = call(anesthesia_mode='propofol_solo',
                 propofol_pct='1%', target_dose=0.2, duration_min=60,
                 diluent_volume=60.0)  # 12 + 60 = 72 ml
        assert r['final_volume'] > 50.0
        assert r['suggested_container'] == 'bolsa_100_ml'

    def test_manual_container_override_accepted(self):
        """El usuario puede seleccionar manualmente un contenedor diferente al sugerido."""
        r = call(anesthesia_mode='propofol_solo',
                 propofol_pct='1%', target_dose=0.1, duration_min=30,
                 diluent_volume=0.0,
                 container_type='jeringa_50_ml')  # override manual
        assert r['selected_container'] == 'jeringa_50_ml'
        # La sugerencia automática se mantiene independiente
        assert r['suggested_container'] == 'jeringa_20_ml'

    def test_selected_container_defaults_to_suggestion(self):
        """Sin override, selected_container == suggested_container."""
        r = call(anesthesia_mode='propofol_solo',
                 propofol_pct='1%', target_dose=0.2, duration_min=60,
                 diluent_volume=20.0,
                 container_type=None)
        assert r['selected_container'] == r['suggested_container']


# ══════════════════════════════════════════════════════════════════════════════
# 7. VALIDACIÓN DE ERRORES DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════

class TestInputValidation:

    def test_zero_weight_raises(self):
        with pytest.raises(ValueError, match='peso'):
            call(weight=0.0, anesthesia_mode='propofol_solo', diluent_volume=0.0)

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError, match='peso'):
            call(weight=-5.0, anesthesia_mode='propofol_solo', diluent_volume=0.0)

    def test_zero_duration_raises(self):
        with pytest.raises(ValueError, match='duración'):
            call(duration_min=0, anesthesia_mode='propofol_solo', diluent_volume=0.0)

    def test_negative_dose_raises(self):
        with pytest.raises(ValueError):
            call(target_dose=-0.1, anesthesia_mode='propofol_solo', diluent_volume=0.0)

    def test_negative_ketamine_dose_raises(self):
        with pytest.raises(ValueError):
            call(anesthesia_mode='propofol_ketamine_mixture',
                 ketamine_target_dose=-0.1, diluent_volume=0.0)

    def test_negative_diluent_raises(self):
        with pytest.raises(ValueError):
            call(anesthesia_mode='propofol_solo', diluent_volume=-5.0)


# ══════════════════════════════════════════════════════════════════════════════
# 8. KETAMINA EDITABLE – ratio 1:2 desactivado permite edición libre
# ══════════════════════════════════════════════════════════════════════════════

class TestKetaminaEditable:

    def test_ketamine_dose_manual_when_ratio_off(self):
        """
        Con use_ratio_1_2=False el usuario puede poner cualquier dosis de ketamina.
        La dosis manual debe usarse tal cual, sin forzar propofol/2.
        """
        # Propofol: 0.2 mg/kg/min → ketamina no forzada a 0.1
        r = call(
            anesthesia_mode='propofol_ketamine_mixture',
            target_dose=0.2, propofol_dose_unit='mg/kg/min',
            ketamine_target_dose=0.3,  # dosis libre, distinta de 0.1
            ketamine_dose_unit='mg/kg/min',
            use_ratio_1_2=False,
            ketamine_concentration=50.0, diluent_volume=0.0,
        )
        # 10 kg × 0.3 mg/kg/min × 60 min = 180 mg ketamina
        assert r['ketamine_total_mg'] == pytest.approx(180.0, abs=1e-2)

    def test_ketamine_dose_auto_when_ratio_on(self):
        """
        Con use_ratio_1_2=True la dosis de ketamina debe ser propofol/2.
        Ignorar el valor manual de ketamine_target_dose.
        Propofol: 0.2 mg/kg/min → ketamina debe ser 0.1 mg/kg/min.
        """
        r = call(
            anesthesia_mode='propofol_ketamine_mixture',
            target_dose=0.2, propofol_dose_unit='mg/kg/min',
            ketamine_target_dose=0.5,  # valor manual ignorado por ratio
            ketamine_dose_unit='mg/kg/min',
            use_ratio_1_2=True,
            ketamine_concentration=50.0, diluent_volume=0.0,
        )
        # Debe usar 0.1 mg/kg/min → 60 mg ketamina en 60 min
        assert r['ketamine_total_mg'] == pytest.approx(60.0, abs=1e-2)

    def test_changing_ketamine_dose_changes_mg(self):
        """Cambiar la dosis manual de ketamina cambia mg totales."""
        r_low = call(
            anesthesia_mode='propofol_ketamine_mixture',
            ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
            use_ratio_1_2=False,
            ketamine_concentration=50.0, diluent_volume=0.0,
        )
        r_high = call(
            anesthesia_mode='propofol_ketamine_mixture',
            ketamine_target_dose=0.4, ketamine_dose_unit='mg/kg/min',
            use_ratio_1_2=False,
            ketamine_concentration=50.0, diluent_volume=0.0,
        )
        assert r_high['ketamine_total_mg'] > r_low['ketamine_total_mg']

    def test_changing_ketamine_dose_changes_ml(self):
        """Cambiar la dosis de ketamina cambia los ml requeridos."""
        r_low = call(
            anesthesia_mode='propofol_ketamine_mixture',
            ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
            use_ratio_1_2=False,
            ketamine_concentration=50.0, diluent_volume=0.0,
        )
        r_high = call(
            anesthesia_mode='propofol_ketamine_mixture',
            ketamine_target_dose=0.4, ketamine_dose_unit='mg/kg/min',
            use_ratio_1_2=False,
            ketamine_concentration=50.0, diluent_volume=0.0,
        )
        assert r_high['ketamine_required_ml'] > r_low['ketamine_required_ml']

    def test_changing_ketamine_dose_changes_final_volume(self):
        """Cambiar la dosis de ketamina cambia el volumen final."""
        r_low = call(
            anesthesia_mode='propofol_ketamine_mixture',
            ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
            use_ratio_1_2=False,
            ketamine_concentration=50.0, diluent_volume=10.0,
        )
        r_high = call(
            anesthesia_mode='propofol_ketamine_mixture',
            ketamine_target_dose=0.4, ketamine_dose_unit='mg/kg/min',
            use_ratio_1_2=False,
            ketamine_concentration=50.0, diluent_volume=10.0,
        )
        assert r_high['final_volume'] > r_low['final_volume']

    def test_changing_ketamine_dose_changes_final_concentration(self):
        """Cambiar la dosis de ketamina cambia la concentración final."""
        r_low = call(
            anesthesia_mode='propofol_ketamine_mixture',
            ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
            use_ratio_1_2=False,
            ketamine_concentration=50.0, diluent_volume=10.0,
        )
        r_high = call(
            anesthesia_mode='propofol_ketamine_mixture',
            ketamine_target_dose=0.4, ketamine_dose_unit='mg/kg/min',
            use_ratio_1_2=False,
            ketamine_concentration=50.0, diluent_volume=10.0,
        )
        assert r_high['final_ketamine_concentration'] > r_low['final_ketamine_concentration']

    def test_ketamine_units_editable_independently(self):
        """
        Sin ratio 1:2, la unidad de ketamina puede ser distinta a propofol.
        6 mg/kg/h == 0.1 mg/kg/min deben dar el mismo total.
        """
        r_min = call(
            anesthesia_mode='propofol_ketamine_mixture',
            target_dose=0.2, propofol_dose_unit='mg/kg/min',
            ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
            use_ratio_1_2=False,
            ketamine_concentration=50.0, diluent_volume=0.0,
        )
        r_h = call(
            anesthesia_mode='propofol_ketamine_mixture',
            target_dose=0.2, propofol_dose_unit='mg/kg/min',
            ketamine_target_dose=6.0, ketamine_dose_unit='mg/kg/h',
            use_ratio_1_2=False,
            ketamine_concentration=50.0, diluent_volume=0.0,
        )
        assert r_h['ketamine_total_mg'] == pytest.approx(r_min['ketamine_total_mg'], abs=1e-2)


# ══════════════════════════════════════════════════════════════════════════════
# 9. SIN CEBADO – VTBI == volumen final, sin dead volume
# ══════════════════════════════════════════════════════════════════════════════

class TestSinCebado:

    def test_propofol_service_does_not_require_priming_params(self):
        """
        calculate_propofol no debe requerir parámetros de cebado.
        La función debe ejecutar sin línea cebada, sin volumen muerto.
        """
        # No pasamos dead_volume ni line_primed
        r = call(anesthesia_mode='propofol_solo', diluent_volume=20.0)
        assert 'final_volume' in r
        assert r['final_volume'] > 0

    def test_vtbi_equals_final_volume_no_dead_volume(self):
        """
        VTBI debe ser exactamente igual al volumen final de la mezcla.
        No se suma ni resta volumen muerto.
        propofol_solo: 10 kg × 0.2 × 60 min = 120 mg / 10 = 12 ml + 20 diluente = 32 ml
        """
        r = call(
            anesthesia_mode='propofol_solo',
            propofol_pct='1%',
            target_dose=0.2, duration_min=60,
            diluent_volume=20.0,
        )
        # VTBI (volumen a infundir) == final_volume sin ajustes de cebado
        assert r['final_volume'] == pytest.approx(32.0, abs=1e-2)

    def test_ketofol_vtbi_no_dead_volume(self):
        """
        En modo Ketofol, VTBI == final_volume (prop_ml + ket_ml + diluent).
        Sin ajuste por dead volume.
        """
        r = call(
            anesthesia_mode='propofol_ketamine_mixture',
            propofol_pct='1%',          # 10 mg/ml
            target_dose=0.2, duration_min=60,
            ketamine_target_dose=0.1, ketamine_dose_unit='mg/kg/min',
            use_ratio_1_2=False,
            ketamine_concentration=50.0, diluent_volume=10.0,
        )
        # propofol: 120 mg / 10 = 12 ml
        # ketamina: 60 mg / 50 = 1.2 ml
        # diluente: 10 ml → total = 23.2 ml
        expected = 12.0 + 1.2 + 10.0
        assert r['final_volume'] == pytest.approx(expected, abs=1e-2)

    def test_volume_guard_uses_final_volume_not_dead_volume(self):
        """
        Volume Guard evalúa el volumen final de mezcla, no incluye dead volume.
        Un volumen final de 32 ml debe ser SAFE independientemente del cebado.
        """
        r = call(
            anesthesia_mode='propofol_solo',
            propofol_pct='1%', target_dose=0.2, duration_min=60,
            diluent_volume=20.0,  # 12 + 20 = 32 ml → SAFE
        )
        assert r['volume_guard_status'] == 'SAFE'
