def calculate_hospital_fluids(weight_kg, species, dehydration_pct, losses_ml, replacement_hours, age_text=""):
    """
    Calcula fluidoterapia para un paciente hospitalizado, usando rangos clínicos.
    
    :param weight_kg: Peso del paciente (kg).
    :param species: "dog" o "cat".
    :param dehydration_pct: Porcentaje de deshidratación (ej. 5 para 5%).
    :param losses_ml: Pérdidas patológicas continuas estimadas (ml).
    :param replacement_hours: Horas para reponer el déficit y pérdidas.
    :param age_text: Texto de edad para detectar cachorros.
    :return: Diccionario con los resultados del cálculo.
    """
    age_lower = str(age_text).lower()
    is_puppy = "mes" in age_lower or "cachorro" in age_lower
    
    # 1. Mantención básica (eligiendo el promedio del rango recomendado)
    if species == "cat":
        # Rango: 50–70 ml/kg/día
        ml_per_kg_day = 60
    else:
        if is_puppy:
            # Rango: 70–100 ml/kg/día
            ml_per_kg_day = 85
        elif weight_kg < 20:
            # Rango: 50–60 ml/kg/día
            ml_per_kg_day = 60
        else:
            # Rango: 40–50 ml/kg/día
            ml_per_kg_day = 50

    maintenance_ml_day = weight_kg * ml_per_kg_day
    maintenance_ml_h = maintenance_ml_day / 24

    # 2. Déficit por deshidratación
    # déficit ml = peso kg × porcentaje deshidratación × 1000
    # Ya que dehydration_pct viene como porcentaje entero (ej. 5), dividimos por 100
    deficit_ml = weight_kg * (dehydration_pct / 100.0) * 1000

    # 3. Volumen total del periodo (reposición)
    # En el periodo de 'replacement_hours', el volumen total es:
    # (mantención por hora * horas de reposición) + déficit + pérdidas
    maintenance_in_period = maintenance_ml_h * replacement_hours
    total_volume_in_period = maintenance_in_period + deficit_ml + losses_ml

    # 4. Parámetros para la bomba
    flow_ml_h = total_volume_in_period / replacement_hours if replacement_hours > 0 else 0
    vtbi_ml = total_volume_in_period

    return {
        "ml_per_kg_day_used": ml_per_kg_day,
        "maintenance_ml_day": round(maintenance_ml_day, 2),
        "maintenance_ml_h": round(maintenance_ml_h, 2),
        "maintenance_in_period": round(maintenance_in_period, 2),
        "deficit_ml": round(deficit_ml, 2),
        "losses_ml": round(losses_ml, 2),
        "total_volume_in_period": round(total_volume_in_period, 2),
        "flow_ml_h": round(flow_ml_h, 2),
        "vtbi_ml": round(vtbi_ml, 2),
        "time_h": replacement_hours
    }
