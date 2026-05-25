def get_fluid_recommendation(main_problem, renal_state, hepatic_state):
    # Rule engine based on clinical recommendations
    if renal_state in ['Oliguria', 'Anuria']:
        return {"fluid": "NaCl 0,9%", "warning": "Evitar cargas de potasio", "justification": "Sugerido por estado renal oligúrico/anúrico."}
    
    if main_problem == "Obstrucción urinaria":
        return {"fluid": "NaCl 0,9%", "warning": "Hiperkalemia frecuente", "justification": "Recomendado para evitar mayor hiperkalemia."}
    
    if main_problem == "Gastroenteritis":
        return {"fluid": "Ringer Lactato", "warning": "Vigilar potasio", "justification": "Primera elección por pérdidas digestivas."}

    if hepatic_state in ['Hepatopatía moderada', 'Hepatopatía severa'] or main_problem == "Hepatopatía":
        return {"fluid": "Plasma-Lyte", "warning": "Menor carga metabólica de lactato", "justification": "Sugerido por estado hepático alterado."}

    if main_problem == "Parvovirosis":
        return {"fluid": "Ringer Lactato", "warning": "Control glucosa", "justification": "Primera elección para parvovirosis."}
        
    if main_problem == "Sepsis":
        return {"fluid": "Cristaloide balanceado (Ej. Ringer Lactato)", "warning": "Revaluación continua", "justification": "Fluidos balanceados preferidos en sepsis."}

    # Default
    return {"fluid": "Ringer Lactato", "warning": "Mantención estándar", "justification": "Fluido de elección general a menos que haya contraindicaciones."}

def calculate_fluid_therapy(weight_kg, dehydration_percent, continuous_losses_ml, main_problem, renal_state, hepatic_state, hours=24):
    deficit_ml = weight_kg * dehydration_percent * 10
    
    # 50 ml/kg/day fixed for Phase 1 for both dog and cat
    maintenance_ml_per_day = weight_kg * 50
    maintenance_ml = maintenance_ml_per_day * (hours / 24.0)
    
    total_volume_ml = deficit_ml + maintenance_ml + continuous_losses_ml
    flow_ml_h = total_volume_ml / hours if hours > 0 else 0
    
    recommendation = get_fluid_recommendation(main_problem, renal_state, hepatic_state)
    
    return {
        "deficit_ml": round(deficit_ml, 2),
        "maintenance_ml": round(maintenance_ml, 2),
        "continuous_losses_ml": round(continuous_losses_ml, 2),
        "total_volume_ml": round(total_volume_ml, 2),
        "flow_ml_h": round(flow_ml_h, 2),
        "hours": hours,
        "recommendation": recommendation
    }
