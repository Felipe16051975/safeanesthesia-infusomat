def calculate_pump(propofol_ml, total_mg, diluent_ml, duration_min, line_primed, prime_fluid, dead_volume_ml=15.0):
    """
    Realiza los cálculos específicos para diluciones y programación de bombas volumétricas (Infusomat Space).
    
    Parámetros:
      - propofol_ml: Volumen de propofol comercial calculado (ml)
      - total_mg: Cantidad teórica de propofol total requerida (mg)
      - diluent_ml: Volumen de cloruro de sodio 0.9% para la dilución (ml)
      - duration_min: Duración estimada del mantenimiento (minutos)
      - line_primed: 'yes' o 'no' (¿La línea está cebada?)
      - prime_fluid: 'suero' o 'mezcla'
      - dead_volume_ml: Volumen muerto estimado de la guía (por defecto 15.0 ml)
    
    Retorna:
      - Un diccionario con volumen final, concentración final, FLOW ml/h, VTBI, retrasos y notas de cebado.
    """
    # 1. Composición de la mezcla
    final_volume = propofol_ml + diluent_ml
    final_concentration = total_mg / final_volume if final_volume > 0 else 0.0
    
    propofol_percentage = (propofol_ml / final_volume * 100.0) if final_volume > 0 else 0.0
    diluent_percentage = (diluent_ml / final_volume * 100.0) if final_volume > 0 else 0.0
    
    # 2. FLOW ml/h para cubrir la duración programada
    duration_h = duration_min / 60.0
    flow_rate = final_volume / duration_h if duration_h > 0 else 0.0
    
    # 3. Alertas por flujo bajo
    pump_alerts = []
    low_flow_limit = 2.0 # ml/h
    
    if flow_rate > 0 and flow_rate < low_flow_limit:
        pump_alerts.append({
            "type": "low_flow",
            "message": f"Tasa de flujo extremadamente baja ({round(flow_rate, 2)} ml/h) para bomba volumétrica estándar (< {low_flow_limit} ml/h). Se sugiere diluir la mezcla en un volumen de suero mayor (ej. pasar a 100 ml de diluyente) para elevar la tasa de flujo y evitar imprecisiones."
        })
        
    # 4. Cebado de línea y volumen muerto
    delay_time_min = 0.0
    vtbi = final_volume
    cebado_notes = ""
    
    if line_primed == 'yes':
        if prime_fluid == 'suero':
            # Si se ceba con suero puro, el fármaco tarda en llegar a la vena del paciente
            if flow_rate > 0:
                delay_time_min = (dead_volume_ml / flow_rate) * 60.0
            cebado_notes = (
                f"Línea cebada con suero. Existirá un retraso terapéutico aproximado de {round(delay_time_min, 1)} minutos "
                "hasta que la mezcla anestésica alcance el torrente circulatorio del paciente."
            )
            # El VTBI a infundir es el volumen final de la mezcla
            vtbi = final_volume
        else:
            # Cebado con la propia mezcla
            cebado_notes = (
                "Línea cebada con mezcla activa de propofol. Administración y efecto clínico inmediatos al encender la bomba. "
                "ADVERTENCIA: La manguera contiene volumen muerto con fármaco activo. Al finalizar el procedimiento, "
                "el remanente de línea NO debe empujarse con bolos rápidos de suero (debe ser desechado) para evitar sobredosis."
            )
            # El VTBI útil a programar es el volumen de mezcla menos el volumen muerto que no se puede infundir
            vtbi = max(0.0, final_volume - dead_volume_ml)
            
    return {
        "final_mixture_volume_ml": round(final_volume, 2),
        "final_concentration_mg_ml": round(final_concentration, 3),
        "propofol_percentage": round(propofol_percentage, 1),
        "diluent_percentage": round(diluent_percentage, 1),
        "flow_ml_h": round(flow_rate, 2),
        "vtbi_ml": round(vtbi, 2),
        "delay_time_min": round(delay_time_min, 1),
        "cebado_notes": cebado_notes,
        "pump_alerts": pump_alerts
    }
