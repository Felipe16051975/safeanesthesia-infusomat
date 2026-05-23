def calculate_hospital_cri(weight_kg, dose, unit, concentration_mg_ml, final_volume_ml, duration_hours):
    """
    Calcula una Infusión Continua (CRI) genérica.
    
    :param weight_kg: Peso del paciente (kg).
    :param dose: Dosis objetivo.
    :param unit: Unidad de la dosis ("mg/kg/h", "mcg/kg/min", "mg/kg/day").
    :param concentration_mg_ml: Concentración comercial del fármaco (mg/ml).
    :param final_volume_ml: Volumen final de la dilución deseado (ml).
    :param duration_hours: Duración de la infusión (horas).
    :return: Diccionario con los resultados del cálculo.
    """
    
    if unit == "mg/kg/h":
        total_mg = dose * weight_kg * duration_hours
    elif unit == "mcg/kg/min":
        # mcg totales por minuto
        mcg_per_min = dose * weight_kg
        # mg totales en la duración (minutos)
        total_mg = (mcg_per_min * (duration_hours * 60)) / 1000.0
    elif unit == "mg/kg/day":
        # mg totales en un día
        mg_per_day = dose * weight_kg
        # mg en la cantidad de horas dadas
        total_mg = mg_per_day * (duration_hours / 24.0)
    else:
        raise ValueError(f"Unidad de dosis no soportada: {unit}")

    # ml a extraer del fármaco
    drug_ml = total_mg / concentration_mg_ml if concentration_mg_ml > 0 else 0

    # ml de suero base a usar
    base_fluid_ml = final_volume_ml - drug_ml
    if base_fluid_ml < 0:
        base_fluid_ml = 0 # No se puede diluir, el volumen final es menor que el fármaco requerido

    # Concentración final en la mezcla
    final_concentration_mg_ml = total_mg / final_volume_ml if final_volume_ml > 0 else 0

    # Parámetros de la bomba
    flow_ml_h = final_volume_ml / duration_hours if duration_hours > 0 else 0
    vtbi_ml = final_volume_ml

    return {
        "total_mg": round(total_mg, 2),
        "drug_ml": round(drug_ml, 2),
        "base_fluid_ml": round(base_fluid_ml, 2),
        "final_volume_ml": round(final_volume_ml, 2),
        "final_concentration_mg_ml": round(final_concentration_mg_ml, 3),
        "flow_ml_h": round(flow_ml_h, 2),
        "vtbi_ml": round(vtbi_ml, 2),
        "time_h": duration_hours
    }
