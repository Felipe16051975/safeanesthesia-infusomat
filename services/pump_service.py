def calculate_pump(
    volume_final: float,
    flow_ml_h: float,
    vtbi_ml: float,
    time_min: float,
    dead_volume_ml: float,
    line_primed: str,
    primed_with: str,
) -> dict:
    """Calculate infusion‑pump related information.

    This function assumes that the propofol dosage and dilution have already
    been computed (e.g. by :func:`services.propofol_service.calculate_propofol`).
    It therefore **does not** recalculate any propofol‑specific values; it only
    handles:
    * therapeutic priming delay when the line is primed with saline,
    * warning when the line is primed with the drug mixture,
    * a low‑flow alarm (< 2 ml/h), and
    * user‑friendly safety messages.
    """

    # Validate inputs (basic sanity checks)
    if volume_final <= 0:
        raise ValueError("volume_final must be > 0")
    if flow_ml_h < 0:
        raise ValueError("flow_ml_h cannot be negative")
    if vtbi_ml <= 0:
        raise ValueError("vtbi_ml must be > 0")
    if time_min <= 0:
        raise ValueError("time_min must be > 0")
    if dead_volume_ml < 0:
        raise ValueError("dead_volume_ml cannot be negative")

    # 1. Low‑flow alarm (threshold 2 ml/h as per original implementation)
    flow_alarm = flow_ml_h < 2.0

    # 2. Priming delay and warning messages
    priming_delay_min = 0.0
    priming_warning = ""

    line_primed = line_primed.strip().lower()
    primed_with = primed_with.strip().lower()

    if line_primed == "si":
        if primed_with == "suero":
            if flow_ml_h > 0:
                priming_delay_min = (dead_volume_ml / flow_ml_h) * 60.0
                priming_warning = (
                    f"Cebado con suero limpio: Se calcula un retraso terapéutico de "
                    f"{round(priming_delay_min, 2)} minutos antes de que el propofol llegue al torrente sanguíneo "
                    f"del paciente a un flujo de {round(flow_ml_h, 2)} ml/h."
                )
            else:
                priming_warning = "Cebado con suero limpio: No se puede calcular el retraso sin un flujo programado."
        elif primed_with == "mezcla":
            priming_warning = (
                "Cebado con mezcla anestésica: El volumen muerto de la línea de infusión contiene "
                "propofol activo. Al finalizar la cirugía, **NO** se debe empujar este volumen residual "
                "(flush rápido), ya que provocaría un bolo de inducción o sobredosis accidental."
            )
        else:
            priming_warning = "Cebado con opción no reconocida; revisar configuración."
    else:
        priming_warning = "La línea no está cebada. Se debe realizar el cebado de seguridad antes de iniciar la infusión."

    return {
        "volume_final": round(volume_final, 2),
        "flow_ml_h": round(flow_ml_h, 2),
        "vtbi_ml": round(vtbi_ml, 2),
        "time_min": time_min,
        "priming_delay_min": round(priming_delay_min, 2),
        "flow_alarm": flow_alarm,
        "priming_warning": priming_warning,
        "safety_message": "Recuerde revisar la presión de la línea y la configuración del Infusomat Space antes de la administración.",
    }
