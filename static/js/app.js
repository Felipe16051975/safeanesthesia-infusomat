document.addEventListener("DOMContentLoaded", () => {
    // --- ELEMENTOS DE FORMULARIO ---
    const calcForm = document.getElementById("calc-form");
    const selectPreset = document.getElementById("diluentVolumePreset");
    const customDiluentWrapper = document.getElementById("custom-diluent-wrapper");
    const inputCustomDiluent = document.getElementById("diluentVolumeCustom");
    const selectLinePrimed = document.getElementById("linePrimed");
    const primedWithWrapper = document.getElementById("primed-with-wrapper");
    
    // --- ELEMENTOS DE RESULTADOS ---
    const outPropPure = document.getElementById("out-propofol-pure");
    const outSaline = document.getElementById("out-saline-diluent");
    const outMixVol = document.getElementById("out-mixture-volume");
    const outMixConc = document.getElementById("out-mixture-concentration");
    const outPropMg = document.getElementById("out-propofol-total-mg");
    const outDelay = document.getElementById("out-priming-delay");
    const delayRow = document.getElementById("delay-row");

    // --- ELEMENTOS DE BOMBA ---
    const pumpFlowVal = document.getElementById("pump-flow-val");
    const pumpVtbiVal = document.getElementById("pump-vtbi-val");
    const pumpTimeVal = document.getElementById("pump-time-val");
    const pumpLowFlowAlarm = document.getElementById("pump-low-flow-alarm");
    const pumpStatusIndicator = document.querySelector(".status-indicator");
    const btnStartStop = document.querySelector(".btn-start-stop");
    const pumpToggleLbl = document.getElementById("pump-toggle-lbl");

    // --- ELEMENTOS DE ALERTA Y BLOQUEO ---
    const safetyLockOverlay = document.getElementById("safety-lock-overlay");
    const criticalConsentCard = document.getElementById("critical-consent-card");
    const consentCheck = document.getElementById("consent-check");
    const alertsContainer = document.getElementById("alerts-container");
    const alertsEmptyMsg = document.getElementById("alerts-empty-msg");

    // --- VARIABLES DE ESTADO ---
    let lastCalculationResult = null;
    let isPumpRunning = false;

    // --- MANEJO DE VISTAS DINÁMICAS EN FORMULARIO ---

    // Mostrar/ocultar volumen de suero personalizado
    selectPreset.addEventListener("change", () => {
        if (selectPreset.value === "custom") {
            customDiluentWrapper.style.display = "block";
            inputCustomDiluent.setAttribute("required", "true");
        } else {
            customDiluentWrapper.style.display = "none";
            inputCustomDiluent.removeAttribute("required");
            inputCustomDiluent.value = "";
        }
    });

    // Mostrar/ocultar cebado
    selectLinePrimed.addEventListener("change", () => {
        if (selectLinePrimed.value === "si") {
            primedWithWrapper.style.display = "block";
        } else {
            primedWithWrapper.style.display = "none";
        }
    });

    // --- ENVÍO DEL CÁLCULO ---

    calcForm.addEventListener("submit", (e) => {
        e.preventDefault();
        runCalculation();
    });

    // Escuchar el cambio en el checkbox de consentimiento
    consentCheck.addEventListener("change", () => {
        if (lastCalculationResult) {
            evaluateConsentAndDisplay(lastCalculationResult);
        }
    });

    function getDiluentVolume() {
        if (selectPreset.value === "custom") {
            return parseFloat(inputCustomDiluent.value) || 0;
        }
        return parseFloat(selectPreset.value) || 0;
    }

    function runCalculation() {
        // Recoger datos
        const payload = {
            patientName: document.getElementById("patientName").value,
            species: document.getElementById("species").value,
            weight: parseFloat(document.getElementById("weight").value),
            age: document.getElementById("age").value,
            asa: document.getElementById("asa").value,
            surgeryType: document.getElementById("surgeryType").value,
            durationMin: parseInt(document.getElementById("durationMin").value, 10),
            propofolConcentration: parseFloat(document.getElementById("propofolConcentration").value),
            targetDose: parseFloat(document.getElementById("targetDose").value),
            diluentVolume: getDiluentVolume(),
            linePrimed: selectLinePrimed.value,
            primedWith: document.getElementById("primedWith").value,
            deadVolume: parseFloat(document.getElementById("deadVolume").value)
        };

        // Desactivar el botón durante la carga
        const btnCalc = document.getElementById("btn-run-calculation");
        btnCalc.disabled = true;
        btnCalc.innerText = "Procesando...";

        fetch("/api/calculate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || "Error desconocido"); });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                lastCalculationResult = data;
                evaluateConsentAndDisplay(data);
            } else {
                alert("Error de cálculo: " + data.error);
            }
        })
        .catch(err => {
            console.error(err);
            alert("Error en la llamada al servidor: " + err.message);
        })
        .finally(() => {
            btnCalc.disabled = false;
            btnCalc.innerText = "Calcular Programación";
        });
    }

    function evaluateConsentAndDisplay(data) {
        const requiresConsent = data.propofol.requires_consent;
        const consentGiven = consentCheck.checked;

        // Renderizar alertas siempre
        renderAlerts(data.propofol.alerts, data.pump.priming_warning, data.pump.flow_alarm);

        if (requiresConsent) {
            criticalConsentCard.style.display = "block";
            
            if (!consentGiven) {
                // Bloquear resultados
                safetyLockOverlay.style.display = "flex";
                resetDisplayOutputs();
                return;
            }
        } else {
            criticalConsentCard.style.display = "none";
        }

        // Desbloquear y renderizar resultados reales
        safetyLockOverlay.style.display = "none";
        renderOutputs(data);
    }

    function resetDisplayOutputs() {
        // Reset valores visuales
        pumpFlowVal.innerText = "0.00";
        pumpVtbiVal.innerText = "0.0 ml";
        pumpTimeVal.innerText = "00:00 h:m";
        pumpLowFlowAlarm.style.display = "none";
        
        outPropPure.innerText = "0.0 ml";
        outSaline.innerText = "0.0 ml";
        outMixVol.innerText = "0.0 ml";
        outMixConc.innerText = "0.00 mg/ml";
        outPropMg.innerText = "0.0 mg";
        outDelay.innerText = "0.0 min";
        
        // Detener la bomba si estaba encendida
        if (isPumpRunning) {
            stopPumpEmulation();
        }
    }

    function renderOutputs(data) {
        const p = data.propofol;
        const pump = data.pump;

        // 1. Plan de preparación
        outPropPure.innerText = `${p.ml_propofol} ml`;
        outSaline.innerText = `${getDiluentVolume()} ml`;
        outMixVol.innerText = `${pump.volume_final} ml`;
        outMixConc.innerText = `${p.final_concentration_mg_ml} mg/ml`;
        outPropMg.innerText = `${p.mg_total} mg`;
        outMgPerMin.innerText = `${p.mg_per_min}`;
        outMgPerHour.innerText = `${p.mg_per_hour}`;

        // Retraso de cebado
        if (pump.priming_delay_min > 0) {
            delayRow.style.display = "flex";
            outDelay.innerText = `${pump.priming_delay_min} min`;
        } else {
            delayRow.style.display = "none";
        }

        // 2. Pantalla Bomba
        pumpFlowVal.innerText = pump.flow_ml_h.toFixed(2);
        pumpVtbiVal.innerText = `${pump.vtbi_ml} ml`;
        
        // Convertir minutos a formato h:m
        const hrs = Math.floor(pump.time_min / 60);
        const mins = pump.time_min % 60;
        const timeFormatted = `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')} h:m`;
        pumpTimeVal.innerText = timeFormatted;

        // Alarma de flujo bajo
        if (pump.flow_alarm) {
            pumpLowFlowAlarm.style.display = "block";
        } else {
            pumpLowFlowAlarm.style.display = "none";
        }
    }

    function renderAlerts(propofolAlerts, primingWarning, flowAlarm) {
        alertsContainer.innerHTML = "";
        
        const allAlerts = [];

        // Agregar alertas de propofol
        propofolAlerts.forEach(alertText => {
            const isCritical = alertText.includes("crítica") || alertText.includes("ASA IV") || alertText.includes("ASA V");
            allAlerts.push({
                text: alertText,
                type: isCritical ? "critical" : "warning"
            });
        });

        // Alarma de flujo bajo
        if (flowAlarm) {
            allAlerts.push({
                text: "Flujo de bomba extremadamente bajo (< 2.0 ml/h). Esto puede comprometer la exactitud de entrega del Infusomat Space y aumentar el riesgo de oclusión.",
                type: "warning"
            });
        }

        // Agregar advertencias de cebado
        if (primingWarning) {
            const isCritical = primingWarning.includes("NO se debe");
            allAlerts.push({
                text: primingWarning,
                type: isCritical ? "critical" : "warning"
            });
        }

        if (allAlerts.length === 0) {
            alertsEmptyMsg.style.display = "block";
            alertsContainer.appendChild(alertsEmptyMsg);
        } else {
            alertsEmptyMsg.style.display = "none";
            allAlerts.forEach(alert => {
                const item = document.createElement("div");
                item.className = `alert-item ${alert.type}`;
                
                const icon = document.createElement("span");
                icon.className = "alert-icon";
                icon.innerHTML = alert.type === "critical" ? "🚨" : "⚠️";
                
                const text = document.createElement("span");
                text.innerText = alert.text;

                item.appendChild(icon);
                item.appendChild(text);
                alertsContainer.appendChild(item);
            });
        }
    }

    // --- EMULACIÓN INTERACTIVA DE START/STOP DE LA BOMBA ---

    btnStartStop.addEventListener("click", () => {
        if (!lastCalculationResult) {
            alert("Debe calcular una programación válida antes de iniciar la bomba.");
            return;
        }

        const requiresConsent = lastCalculationResult.propofol.requires_consent;
        if (requiresConsent && !consentCheck.checked) {
            alert("No se puede iniciar la bomba: requiere aceptar la advertencia de responsabilidad.");
            return;
        }

        if (isPumpRunning) {
            stopPumpEmulation();
        } else {
            startPumpEmulation();
        }
    });

    function startPumpEmulation() {
        isPumpRunning = true;
        pumpStatusIndicator.innerText = "RUN";
        pumpStatusIndicator.classList.remove("run");
        pumpStatusIndicator.classList.add("active-running");
        pumpToggleLbl.innerText = "STOP";
        btnStartStop.style.background = "#c53030"; // Botón se vuelve rojo para detener
        btnStartStop.style.borderColor = "#9b2c2c";
    }

    function stopPumpEmulation() {
        isPumpRunning = false;
        pumpStatusIndicator.innerText = "STOP";
        pumpStatusIndicator.classList.remove("active-running");
        pumpStatusIndicator.classList.add("run");
        pumpToggleLbl.innerText = "START";
        btnStartStop.style.background = "#2f855a"; // Botón vuelve a verde
        btnStartStop.style.borderColor = "#22543d";
    }
});
