/**
 * SafeAnesthesia Infusomat Propofol Module
 * CONTROLADOR PRINCIPAL DEL FRONTEND (REACTIVIDAD Y CAPA DE SERVICIOS)
 */

document.addEventListener('DOMContentLoaded', async () => {
    // 1. CONTROL DE CONSENTIMIENTO INELUDIBLE (Session-based)
    const consentModal = document.getElementById('consent-modal');
    const btnAcceptConsent = document.getElementById('btn-accept-consent');
    
    if (sessionStorage.getItem('clinical_consent_signed') === 'true') {
        if (consentModal) consentModal.classList.add('hidden');
    } else {
        if (consentModal) consentModal.classList.remove('hidden');
    }

    if (btnAcceptConsent) {
        btnAcceptConsent.addEventListener('click', () => {
            sessionStorage.setItem('clinical_consent_signed', 'true');
            if (consentModal) consentModal.classList.add('hidden');
        });
    }

    // ==========================================
    // VARIABLES Y ESTADO GLOBAL DE LA APP
    // ==========================================
    let CLINICAL_LIMITS = {};
    let SURGERY_PROFILES = {};
    let activeCaseId = null; // null para casos nuevos, ID numérico si editamos o duplicamos
    let ketamineEvents = []; // Lista de refuerzos temporales
    // Ensure global alert arrays exist
    window.alerts = window.alerts || [];
    window.pump_alerts = window.pump_alerts || [];

    // Carga inicial de límites consolidados
    await loadClinicalLimits();
    await loadHistoryAndDashboard();
    await loadAuditTerminal();

    // ==========================================
    // CAPTURA Y GESTIÓN DE CONFIGURACIÓN JSON
    // ==========================================
    async function loadClinicalLimits() {
        try {
            const response = await fetch('/api/limits');
            const data = await response.json();
            CLINICAL_LIMITS = data;
            
            // Cargar perfiles quirúrgicos en la interfaz
            SURGERY_PROFILES = data.surgeries.profiles || {};
            
            // Actualizar referencias clínicas visuales
            updateDoseReference();
        } catch (error) {
            console.error('Error cargando límites clínicos:', error);
        }
    }

    // ==========================================
    // INTERACTIVIDAD FRONTEND Y COMPORTAMIENTO UI
    // ==========================================
    
    // Cambios de Especie e inputs dinámicos de dosificación
    const speciesSelect = document.getElementById('species');
    if (speciesSelect) {
        speciesSelect.addEventListener('change', () => {
            updateDoseReference();
            // Si el cálculo está activo, disparar recálculo de dosis máxima local de lidocaína
            recalculateLidocaineToxicity();
        });
    }

    function updateDoseReference() {
        const species = speciesSelect ? speciesSelect.value : 'dog';
        if (CLINICAL_LIMITS.propofol && CLINICAL_LIMITS.propofol.limits) {
            const lim = CLINICAL_LIMITS.propofol.limits[species];
            const refText = document.getElementById('propofol-limits-ref');
            if (refText) {
                refText.innerText = `Límites de referencia: Min ${lim.minDose} | Max ${lim.maxDose} | Advertencia ${lim.warningThreshold} | Crítico ${lim.criticalThreshold} mg/kg/min`;
            }
        }
    }

    // Cambios en tipo de cirugía y despliegue de perfiles con puntos críticos
    const surgerySelect = document.getElementById('surgery_type');
    const surgeryProfileCard = document.getElementById('surgery-profile-card');
    const surgeryProfileName = document.getElementById('surgery-profile-name');
    const surgeryCriticalPoints = document.getElementById('surgery-critical-points');

    if (surgerySelect) {
        surgerySelect.addEventListener('change', () => {
            const selected = surgerySelect.value;
            if (SURGERY_PROFILES[selected]) {
                const profile = SURGERY_PROFILES[selected];
                if (surgeryProfileName) surgeryProfileName.innerText = `Puntos Críticos de Monitoreo: ${profile.name}`;
                if (surgeryCriticalPoints) {
                    surgeryCriticalPoints.innerHTML = '';
                    if (Array.isArray(profile.criticalPoints)) {
                        profile.criticalPoints.forEach(pt => {
                            const li = document.createElement('li');
                            li.innerText = pt;
                            surgeryCriticalPoints.appendChild(li);
                        });
                    }
                }
                if (surgeryProfileCard) surgeryProfileCard.classList.remove('hidden');
                
                // Habilitar/Deshabilitar refuerzos según perfil quirúrgico
                const btnAddKetamine = document.getElementById('btn-add-ketamine');
                if (btnAddKetamine) {
                    btnAddKetamine.disabled = !profile.allowsKetamine;
                }
            } else {
                if (surgeryProfileCard) surgeryProfileCard.classList.add('hidden');
            }
        });
    }

    // Modalidad Operativa: Cálculo Solamente vs. Programación Infusomat
    const calculationModeInputs = document.getElementsByName('calculation_mode');
    calculationModeInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            toggleCalculationMode(e.target.value);
        });
    });

    function toggleCalculationMode(mode) {
        const secDilution = document.getElementById('section-dilution');
        const secPriming = document.getElementById('section-priming');
        const secBomba = document.getElementById('section-bomba-simulator');
        const pumpRows = document.querySelectorAll('.row-pump-only');

        if (mode === 'infusomat') {
            if (secDilution) secDilution.classList.remove('hidden');
            if (secPriming) secPriming.classList.remove('hidden');
            if (secBomba) secBomba.classList.remove('hidden');
            pumpRows.forEach(row => row.classList.remove('hidden'));
        } else {
            if (secDilution) secDilution.classList.add('hidden');
            if (secPriming) secPriming.classList.add('hidden');
            if (secBomba) secBomba.classList.add('hidden');
            pumpRows.forEach(row => row.classList.add('hidden'));
        }
    }

    // Botones rápidos de volumen de diluyente
    const quickVolBtns = document.querySelectorAll('.btn-quick-vol');
    const diluentVolumeInput = document.getElementById('diluent_volume');
    
    quickVolBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (diluentVolumeInput) {
                diluentVolumeInput.value = btn.getAttribute('data-vol');
                // Disparar evento input para cálculos reactivos en vivo
                diluentVolumeInput.dispatchEvent(new Event('input'));
            }
        });
    });

    // Cambios de cebado
    const linePrimedSelect = document.getElementById('line_primed');
    const linePrimedOptions = document.querySelectorAll('.line-primed-options');
    
    if (linePrimedSelect) {
        linePrimedSelect.addEventListener('change', () => {
            if (linePrimedSelect.value === 'yes') {
                linePrimedOptions.forEach(opt => opt.classList.remove('hidden'));
            } else {
                linePrimedOptions.forEach(opt => opt.classList.add('hidden'));
            }
        });
    }

    // ==============================
    // PRIMING VOLUME SELECTOR LOGIC
    // ==============================
    const primingVolumeSelect = document.getElementById('priming_volume_selector');
    const customPrimingInput = document.getElementById('custom_priming_volume');
    const deadVolumeInput = document.getElementById('dead_volume_ml');

    function updatePrimingVolume() {
        if (!primingVolumeSelect || !deadVolumeInput) return;
        const val = primingVolumeSelect.value;
        if (val === 'custom') {
            customPrimingInput.classList.remove('hidden');
            deadVolumeInput.value = customPrimingInput.value || '';
        } else {
            customPrimingInput.classList.add('hidden');
            let mapped = 0;
            if (val === 'short') mapped = 2;
            else if (val === 'standard') mapped = 22;
            else if (val === 'long') mapped = 40;
            deadVolumeInput.value = mapped;
        }
    }

    if (primingVolumeSelect) {
        primingVolumeSelect.addEventListener('change', updatePrimingVolume);
    }
    if (customPrimingInput) {
        customPrimingInput.addEventListener('input', () => {
            deadVolumeInput.value = customPrimingInput.value;
        });
    }

    if (btnCalculate) {
        btnCalculate.addEventListener('click', async () => {
            await executePlanCalculation();
        });
    }

    async function executePlanCalculation(bypassCritical = false) {
        // Capturar campos
        const pName = document.getElementById('patient_name').value;
        const species = document.getElementById('species').value;
        const breed = document.getElementById('breed').value;
        const weight = parseFloat(document.getElementById('weight').value);
        const age = document.getElementById('age').value;
        const asa = document.getElementById('asa_class').value;
        const surgery = document.getElementById('surgery_type').value;
        const duration = parseFloat(document.getElementById('duration_estimated').value);
        const dose = parseFloat(document.getElementById('target_dose').value);
        const concentration = document.getElementById('propofol_concentration').value;
        const calcMode = document.querySelector('input[name="calculation_mode"]:checked').value;

        if (!pName || isNaN(weight) || isNaN(duration) || isNaN(dose)) {
            alert('Por favor complete todos los datos requeridos (*) del paciente y dosis.');
            return;
        }

        // 1. Consultar motor clínico de Propofol en backend
        const propPayload = {
            patient_name: pName,
            weight: weight,
            target_dose: dose,
            duration_estimated: duration,
            species: species,
            propofol_concentration: concentration,
            asa_class: asa
        };

        try {
            const propRes = await fetch('/api/calculate/propofol', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(propPayload)
            });

            const propData = await propRes.json();
            if (!propRes.ok) {
                alert(`Error clínico: ${propData.error}`);
                return;
            }

            // Evaluar Alerta Crítica (ASA IV/V o dosis excesiva)
            const criticalCard = document.getElementById('critical-alert-card');
            const criticalMsg = document.getElementById('critical-alert-messages');
            const chkAcceptCritical = document.getElementById('chk-accept-critical');

            if (propData.alert_level === 'CRITICAL' && !bypassCritical) {
                if (criticalCard && criticalMsg) {
                    criticalMsg.innerHTML = '';
                    if (Array.isArray(propData.alerts)) {
                        propData.alerts.forEach(al => {
                            const div = document.createElement('div');
                            div.className = 'clinical-warning-box text-left mb-2';
                            div.innerHTML = `<strong>${al.type.toUpperCase()}:</strong> ${al.message}`;
                            criticalMsg.appendChild(div);
                        });
                    }
                    criticalCard.classList.remove('hidden');
                    
                    // Escuchar confirmación ineludible
                    if (chkAcceptCritical) {
                        chkAcceptCritical.checked = false;
                        chkAcceptCritical.onchange = () => {
                            if (chkAcceptCritical.checked) {
                                criticalCard.classList.add('hidden');
                                executePlanCalculation(true); // Recalcular con bypass
                            }
                        };
                    }
                }
                return; // Detener flujo hasta confirmación del clínico
            }

            // Rellenar resultados teóricos
            document.getElementById('res-mg-min').innerText = propData.mg_min;
            document.getElementById('res-mg-h').innerText = propData.mg_h;
            document.getElementById('res-total-mg').innerText = propData.total_mg;
            document.getElementById('res-propofol-ml').innerText = propData.required_ml;

            // Limpiar alertas críticas si ya se confirmaron
            if (criticalCard) criticalCard.classList.add('hidden');

            // 2. Advertencias ordinarias (ASA III, Gatos)
            const warningCard = document.getElementById('warning-alerts-card');
            const warningMsg = document.getElementById('warning-alert-messages');
            
            if (warningCard && warningMsg) {
                warningMsg.innerHTML = '';
                const warnings = propData.alerts.filter(al => al.type.includes('warning') || al.type.includes('phenolic'));
                if (warnings.length > 0) {
                    warnings.forEach(w => {
                        const p = document.createElement('p');
                        p.className = 'mb-1';
                        p.innerHTML = `• <strong>${w.type.toUpperCase()}:</strong> ${w.message}`;
                        warningMsg.appendChild(p);
                    });
                    warningCard.classList.remove('hidden');
                } else {
                    warningCard.classList.add('hidden');
                }
            }

            // 3. Cálculos de mezcla y bomba (Solo en modo Infusomat)
            if (calcMode === 'infusomat') {
                const diluentVal = parseFloat(document.getElementById('diluent_volume').value);
                const isPrimed = document.getElementById('line_primed').value;
                const pFluid = document.getElementById('prime_fluid').value;
                const deadVol = parseFloat(document.getElementById('dead_volume_ml').value);

                if (isNaN(diluentVal)) {
                    alert('Por favor defina un volumen de diluyente NaCl 0,9%.');
                    return;
                }

                const pumpPayload = {
                    propofol_ml: propData.required_ml,
                    total_mg: propData.total_mg,
                    diluent_volume: diluentVal,
                    duration_estimated: duration,
                    line_primed: isPrimed,
                    prime_fluid: pFluid,
                    dead_volume_ml: deadVol
                };

                const pumpRes = await fetch('/api/calculate/pump', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(pumpPayload)
                });

                const pumpData = await pumpRes.json();
                
                // Actualizar bomba LCD
                document.getElementById('lcd-flow-val').innerText = pumpData.flow_ml_h;
                document.getElementById('lcd-vtbi-val').innerText = pumpData.vtbi_ml;
                
                // Formatear Duración hh:mm
                const hours = Math.floor(duration / 60);
                const mins = Math.round(duration % 60);
                document.getElementById('lcd-time-val').innerHTML = `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')} <small>hh:mm</small>`;
                document.getElementById('lcd-pump-status').innerText = 'RUNNING';
                document.getElementById('res-delay-time').innerText = pumpData.delay_time_min;

                // ------------------------------
                // PREPARACIÓN CLÍNICA RESUMIDA
                // ------------------------------
                const prepDiv = document.getElementById('preparation-result');
                if (prepDiv) {
                    const propMl = propData.required_ml;
                    const propConc = concentration; // e.g., "1%" or "2%"
                    const diluent = diluentVal;
                    const finalVol = propMl + diluent;
                    const finalConc = pumpData.final_concentration_mg_ml;
                    prepDiv.innerHTML = `
                        <p><strong>Preparación:</strong> Extraer ${propMl} ml de propofol ${propConc}. Agregar a ${diluent} ml de NaCl 0,9%.</p>
                        <p>Volumen final: ${finalVol} ml.</p>
                        <p>Concentración final: ${finalConc} mg/ml.</p>
                    `;
                    prepDiv.classList.remove('hidden');
                }

                // Dibujar composición visual
                document.getElementById('bar-propofol').style.width = `${pumpData.propofol_percentage}%`;
                document.getElementById('bar-propofol').innerText = `Propofol ${pumpData.propofol_percentage}%`;
                document.getElementById('bar-saline').style.width = `${pumpData.diluent_percentage}%`;
                document.getElementById('bar-saline').innerText = `NaCl ${pumpData.diluent_percentage}%`;
                
                document.getElementById('lbl-propofol-composition').innerText = `${propData.required_ml} ml (${pumpData.propofol_percentage}%)`;
                document.getElementById('lbl-saline-composition').innerText = `${diluentVal} ml (${pumpData.diluent_percentage}%)`;
                document.getElementById('lbl-mix-concentration').innerText = `${pumpData.final_concentration_mg_ml} mg/ml`;
                document.getElementById('mixture-composition-box').classList.remove('hidden');

                // Anexar alertas de bomba (bajo flujo) a las advertencias
                if (pumpData.pump_alerts.length > 0 && warningMsg && warningCard) {
                    warningCard.classList.remove('hidden');
                    if (Array.isArray(pumpData.pump_alerts) && pumpData.pump_alerts.length > 0) {
                        pumpData.pump_alerts.forEach(pal => {
                            const p = document.createElement('p');
                            p.className = 'mb-1 color-yellow font-bold';
                            p.innerHTML = `• <strong>${pal.type.toUpperCase()}:</strong> ${pal.message}`;
                            warningMsg.appendChild(p);
                        });
                    }
                }
            } else {
                // Cálculo simple (Cálculo Solamente)
                document.getElementById('mixture-composition-box').classList.add('hidden');
            }

            // Desbloquear secciones del transoperatorio y guardado
            document.getElementById('section-intraoperatorio').classList.remove('hidden');
            document.getElementById('card-action-controls').classList.remove('hidden');
            
            // Inicializar balances límites en UI
            recalculateLidocaineToxicity();

        } catch (error) {
            console.error('Error procesando cálculos de mantenimiento:', error);
        }
    }

    // ==========================================
    // REFUERZOS KETAMINA (Fase G)
    // ==========================================
    const btnAddKetamine = document.getElementById('btn-add-ketamine');
    if (btnAddKetamine) {
        btnAddKetamine.addEventListener('click', async () => {
            const weight = parseFloat(document.getElementById('weight').value);
            const kDose = parseFloat(document.getElementById('ketamine_dose').value);
            const kConc = parseFloat(document.getElementById('ketamine_conc').value);
            const kReason = document.getElementById('ketamine_reason').value || "Refuerzo transquirúrgico";

            if (isNaN(weight) || isNaN(kDose) || isNaN(kConc)) {
                alert('Ingrese peso y dosis de ketamina.');
                return;
            }

            const payload = {
                weight: weight,
                target_dose_mg_kg: kDose,
                concentration_mg_ml: kConc
            };

            try {
                const res = await fetch('/api/calculate/ketamine', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await res.json();
                
                // Obtener hora actual del cliente
                const now = new Date();
                const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

                // Registrar en la lista
                const newEvent = {
                    time_registered: timeStr,
                    dose_mg_kg: kDose,
                    volume_ml: data.required_ml,
                    reason: kReason
                };
                
                ketamineEvents.push(newEvent);
                renderKetamineEvents();
                
                // Limpiar campos secundarios
                document.getElementById('ketamine_reason').value = '';
                
            } catch (error) {
                console.error('Error calculando bolo de ketamina:', error);
            }
        });
    }

    function renderKetamineEvents() {
        const container = document.getElementById('ketamine-event-log');
        if (!container) return;
        
        container.innerHTML = '';
        if (ketamineEvents.length === 0) {
            container.innerHTML = '<span class="text-xs text-slate">No hay bolos registrados.</span>';
            return;
        }

        ketamineEvents.forEach((ev, idx) => {
            const div = document.createElement('div');
            div.className = 'event-log-row flex-row justify-between text-xs p-1 mb-1 bg-slate rounded';
            div.innerHTML = `
                <span><strong>${ev.time_registered}</strong> | Ketamina bolo: ${ev.dose_mg_kg} mg/kg (${ev.volume_ml} ml) - ${ev.reason}</span>
                <button type="button" class="btn btn-danger btn-xs btn-remove-ket" data-idx="${idx}" style="padding:0 0.2rem; font-size:10px;">X</button>
            `;
            container.appendChild(div);
        });

        // Vincular botón de eliminación
        document.querySelectorAll('.btn-remove-ket').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(btn.getAttribute('data-idx'));
                ketamineEvents.splice(idx, 1);
                renderKetamineEvents();
            });
        });
    }

    // ==========================================
    // TOXICIDAD LIDOCAÍNA LOCAL (Fase G)
    // ==========================================
    const lidoInputs = document.querySelectorAll('.lido-input');
    lidoInputs.forEach(input => {
        input.addEventListener('input', () => {
            recalculateLidocaineToxicity();
        });
    });

    const lidoMaxDoseInput = document.getElementById('lidocaine_max_dose');
    const lidoConcSelect = document.getElementById('lidocaine_conc_pct');

    if (lidoMaxDoseInput) {
        lidoMaxDoseInput.addEventListener('input', () => recalculateLidocaineToxicity());
    }
    if (lidoConcSelect) {
        lidoConcSelect.addEventListener('change', () => recalculateLidocaineToxicity());
    }

    async function recalculateLidocaineToxicity() {
        const weight = parseFloat(document.getElementById('weight').value);
        const species = document.getElementById('species').value;
        const conc = parseFloat(document.getElementById('lidocaine_conc_pct').value);
        
        const linea = parseFloat(document.getElementById('lido_linea_alba').value) || 0.0;
        const lig = parseFloat(document.getElementById('lido_ligamento').value) || 0.0;
        const per = parseFloat(document.getElementById('lido_peritoneal').value) || 0.0;
        const piel = parseFloat(document.getElementById('lido_piel').value) || 0.0;

        if (isNaN(weight)) return;

        // Si la dosis límite no está escrita, sugerirla basada en la configuración cargada
        if (!lidoMaxDoseInput.value && CLINICAL_LIMITS.lidocaine && CLINICAL_LIMITS.lidocaine.limits) {
            lidoMaxDoseInput.value = CLINICAL_LIMITS.lidocaine.limits[species].maxSafeDose;
        }

        const payload = {
            weight: weight,
            species: species,
            concentration_pct: conc,
            linea_alba_ml: linea,
            ligamento_ml: lig,
            peritoneal_ml: per,
            piel_ml: piel
        };

        try {
            const res = await fetch('/api/calculate/lidocaine', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            
            // Actualizar interfaz
            document.getElementById('lbl-lido-accumulated').innerText = `${data.total_ml_used} ml / ${data.total_mg_used} mg`;
            document.getElementById('lbl-lido-percentage').innerText = `${data.percentage_consumed}%`;
            document.getElementById('lbl-lido-safe-balance').innerText = `${data.remaining_ml} ml`;

            // Barra de progreso y colores
            const bar = document.getElementById('lido-toxicity-bar');
            if (bar) {
                bar.style.width = `${Math.min(100, data.percentage_consumed)}%`;
                bar.className = 'progress-bar-fill'; // reset
                
                if (data.status === 'CRITICAL') {
                    bar.classList.add('pct-100');
                    // Mostrar alerta de toxicidad
                    alert(data.alerts[0].message);
                } else if (data.status === 'WARNING') {
                    bar.classList.add('pct-80-99');
                } else {
                    bar.classList.add('pct-0-79');
                }
            }

        } catch (error) {
            console.error('Error evaluando toxicidad de lidocaína local:', error);
        }
    }

    // ==========================================
    // ANÁLISIS DE DOSIS REAL DEL PROPONENTE (Fase H)
    // ==========================================
    const durationRealInput = document.getElementById('duration_real');
    const volRealInput = document.getElementById('actual_volume_infused');

    if (durationRealInput) durationRealInput.addEventListener('input', () => recalculateRealDosePerformance());
    if (volRealInput) volRealInput.addEventListener('input', () => recalculateRealDosePerformance());

    function recalculateRealDosePerformance() {
        const durationReal = parseFloat(durationRealInput.value);
        const volReal = parseFloat(volRealInput.value);
        const weight = parseFloat(document.getElementById('weight').value);
        const mixConcentration = parseFloat(document.getElementById('lbl-mix-concentration').innerText) || 10.0; 
        
        if (isNaN(durationReal) || isNaN(volReal) || isNaN(weight) || durationReal <= 0) {
            document.getElementById('real-dose-analysis-box').classList.add('hidden');
            return;
        }

        const realMg = volReal * mixConcentration;
        const realMgKg = realMg / weight;
        const realDoseRate = realMgKg / durationReal;

        document.getElementById('res-real-propofol-mg').innerText = realMg.toFixed(2);
        document.getElementById('res-real-mg-kg').innerText = realMgKg.toFixed(2);
        document.getElementById('res-real-avg-dose-rate').innerText = realDoseRate.toFixed(3);

        document.getElementById('real-dose-analysis-box').classList.remove('hidden');
    }

    // ==========================================
    // PERSISTENCIA: GUARDAR CASO CLÍNICO
    // ==========================================
    const btnSaveCase = document.getElementById('btn-save-case');
    if (btnSaveCase) {
        btnSaveCase.addEventListener('click', async () => {
            const pName = document.getElementById('patient_name').value;
            const species = document.getElementById('species').value;
            const breed = document.getElementById('breed').value;
            const weight = parseFloat(document.getElementById('weight').value);
            const age = document.getElementById('age').value;
            const asa = document.getElementById('asa_class').value;
            const surgery = document.getElementById('surgery_type').value;
            const durationEst = parseFloat(document.getElementById('duration_estimated').value);
            const durationReal = parseFloat(document.getElementById('duration_real').value);
            const calcMode = document.querySelector('input[name="calculation_mode"]:checked').value;
            
            const targetDose = parseFloat(document.getElementById('target_dose').value);
            const propConc = document.getElementById('propofol_concentration').value;

            // Datos transoperatorios
            const fc = parseInt(document.getElementById('fc').value);
            const fr = parseInt(document.getElementById('fr').value);
            const spo2 = parseInt(document.getElementById('spo2').value);
            const pas = parseInt(document.getElementById('pas').value);
            const pam = parseInt(document.getElementById('pam').value);
            const temp = parseFloat(document.getElementById('temp').value);
            const etco2 = parseInt(document.getElementById('etco2').value);

            const volReal = parseFloat(document.getElementById('actual_volume_infused').value);
            const notes = document.getElementById('notes').value;

            // Mezclas y bomba
            const diluentVal = parseFloat(document.getElementById('diluent_volume').value) || 0.0;
            const flow = parseFloat(document.getElementById('lcd-flow-val').innerText) || 0.0;
            const vtbi = parseFloat(document.getElementById('lcd-vtbi-val').innerText) || 0.0;
            const primed = document.getElementById('line_primed').value;
            const pFluid = document.getElementById('prime_fluid').value;
            const deadVol = parseFloat(document.getElementById('dead_volume_ml').value) || 15.0;

            const totalPropMg = parseFloat(document.getElementById('res-total-mg').innerText) || 0.0;
            const finalMixVol = parseFloat(document.getElementById('mixture-composition-box').classList.contains('hidden') ? 0.0 : document.getElementById('res-propofol-ml').innerText) || 0.0;
            const finalConc = parseFloat(document.getElementById('lbl-mix-concentration').innerText) || 10.0;

            // Lidocaina
            const linea = parseFloat(document.getElementById('lido_linea_alba').value) || 0.0;
            const lig = parseFloat(document.getElementById('lido_ligamento').value) || 0.0;
            const per = parseFloat(document.getElementById('lido_peritoneal').value) || 0.0;
            const piel = parseFloat(document.getElementById('lido_piel').value) || 0.0;
            const lidoTotalMg = parseFloat(document.getElementById('lbl-lido-accumulated').innerText.split('/')[1]) || 0.0;
            const lidoPct = parseFloat(document.getElementById('lbl-lido-percentage').innerText) || 0.0;

            // Auditoría Real
            const realMg = volReal * finalConc;
            const realMgKg = realMg / weight;
            const realAvgDose = realMgKg / durationReal;

            const casePayload = {
                id: activeCaseId,
                patient_name: pName,
                species: species,
                breed: breed,
                weight: weight,
                age: age,
                asa_class: asa,
                surgery_type: surgery,
                duration_estimated: durationEst,
                duration_real: isNaN(durationReal) ? null : durationReal,
                calculation_mode: calcMode,
                
                propofol_concentration: propConc,
                target_dose: targetDose,
                diluent_volume: diluentVal,
                final_mixture_volume: finalMixVol + diluentVal,
                final_concentration: finalConc,
                total_propofol_mg: totalPropMg,
                
                flow_ml_h: flow,
                vtbi_ml: vtbi,
                line_primed: primed,
                prime_fluid: pFluid,
                dead_volume_ml: deadVol,
                delay_time_min: parseFloat(document.getElementById('res-delay-time').innerText) || 0.0,

                fc: isNaN(fc) ? null : fc,
                fr: isNaN(fr) ? null : fr,
                spo2: isNaN(spo2) ? null : spo2,
                pas: isNaN(pas) ? null : pas,
                pam: isNaN(pam) ? null : pam,
                temp: isNaN(temp) ? null : temp,
                etco2: isNaN(etco2) ? null : etco2,
                
                actual_volume_infused: isNaN(volReal) ? null : volReal,
                actual_propofol_mg: isNaN(realMg) ? null : realMg,
                actual_mg_kg: isNaN(realMgKg) ? null : realMgKg,
                actual_avg_dose_rate: isNaN(realAvgDose) ? null : realAvgDose,
                notes: notes,
                
                ketamine_events: ketamineEvents,
                lidocaine_event: {
                    linea_alba_ml: linea,
                    ligamento_ml: lig,
                    peritoneal_ml: per,
                    piel_ml: piel,
                    total_mg: lidoTotalMg,
                    percentage_of_max: lidoPct
                }
            };

            try {
                const res = await fetch('/api/cases/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(casePayload)
                });

                const result = await res.json();
                if (result.success) {
                    alert(result.message);
                    activeCaseId = null; // Reiniciar estado
                    ketamineEvents = [];
                    renderKetamineEvents();
                    
                    // Recargar tablas e historial
                    await loadHistoryAndDashboard();
                    await loadAuditTerminal();
                } else {
                    alert(`Error: ${result.message}`);
                }
            } catch (error) {
                console.error('Error al guardar procedimiento:', error);
            }
        });
    }

    // ==========================================
    // HISTORIAL Y DASHBOARD (CRUD BINDINGS)
    // ==========================================
    async function loadHistoryAndDashboard() {
        try {
            const res = await fetch('/api/cases');
            const data = await res.json();
            
            const tbody = document.getElementById('history-table-body');
            if (!tbody) return;
            
            tbody.innerHTML = '';
            
            let todayCount = 0;
            let totalRealTime = 0;
            let ovhCount = 0;
            let castCount = 0;
            let realTimeCount = 0;
            
            const todayStr = new Date().toISOString().split('T')[0];

            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="text-center text-slate">No hay registros de anestesias en el historial.</td></tr>';
            } else {
                data.forEach(c => {
                    // Contadores de Dashboard
                    if (c.date === todayStr) todayCount++;
                    if (c.duration_real) {
                        totalRealTime += c.duration_real;
                        realTimeCount++;
                    }
                    if (c.surgery_type === 'ovh') ovhCount++;
                    if (c.surgery_type === 'castration') castCount++;

                    // Dibujar fila
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${c.date}</td>
                        <td><strong>${c.patient_name}</strong> <small>(${c.species === 'dog' ? 'Perro' : 'Gato'})</small></td>
                        <td>${c.surgery_type.toUpperCase()}</td>
                        <td>${c.weight} kg</td>
                        <td>ASA ${c.asa_class}</td>
                        <td>${c.duration_real ? c.duration_real + ' min' : '--'}</td>
                        <td class="font-bold color-teal">${c.actual_avg_dose_rate ? c.actual_avg_dose_rate.toFixed(3) + ' mg/kg/min' : '--'}</td>
                        <td>
                            <button class="btn btn-outline btn-sm btn-use-template" data-id="${c.id}">Plantilla</button>
                            <button class="btn btn-outline btn-sm btn-print-pdf" data-id="${c.id}">PDF</button>
                            <button class="btn btn-outline btn-sm btn-export-parten" data-id="${c.id}" ${c.exported ? 'style="border-color:#10b981; color:#10b981;"' : ''}>${c.exported ? 'Sincronizado' : 'Exportar'}</button>
                            <button class="btn btn-danger btn-sm btn-delete-case" data-id="${c.id}">Eliminar</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }

            // Actualizar widgets del Dashboard
            document.getElementById('stat-today').innerText = todayCount;
            document.getElementById('stat-avg-time').innerHTML = realTimeCount > 0 ? `${Math.round(totalRealTime / realTimeCount)} <small>min</small>` : `0 <small>min</small>`;
            document.getElementById('stat-ovh').innerText = ovhCount;
            document.getElementById('stat-castration').innerText = castCount;

            // Vincular botones dinámicos del historial
            bindHistoryButtons();

        } catch (error) {
            console.error('Error cargando historial de cirugías:', error);
        }
    }

    function bindHistoryButtons() {
        // 1. Botón usar como plantilla (Duplicar)
        document.querySelectorAll('.btn-use-template').forEach(btn => {
            btn.addEventListener('click', async () => {
                const caseId = btn.getAttribute('data-id');
                try {
                    const res = await fetch(`/api/cases/${caseId}`);
                    const c = await res.json();
                    
                    // Precargar datos del paciente y dosis en inputs
                    document.getElementById('patient_name').value = c.patient_name;
                    document.getElementById('species').value = c.species;
                    document.getElementById('species').dispatchEvent(new Event('change'));
                    
                    document.getElementById('breed').value = c.breed;
                    document.getElementById('weight').value = c.weight;
                    document.getElementById('age').value = c.age;
                    document.getElementById('asa_class').value = c.asa_class;
                    
                    document.getElementById('surgery_type').value = c.surgery_type;
                    document.getElementById('surgery_type').dispatchEvent(new Event('change'));
                    
                    document.getElementById('duration_estimated').value = c.duration_estimated;
                    document.getElementById('target_dose').value = c.target_dose;
                    document.getElementById('propofol_concentration').value = c.propofol_concentration;
                    
                    // Cargar modo operativo
                    const modeRdo = document.querySelector(`input[name="calculation_mode"][value="${c.calculation_mode}"]`);
                    if (modeRdo) {
                        modeRdo.checked = true;
                        toggleCalculationMode(c.calculation_mode);
                    }
                    
                    if (c.calculation_mode === 'infusomat') {
                        document.getElementById('diluent_volume').value = c.diluent_volume;
                        document.getElementById('line_primed').value = c.line_primed;
                        document.getElementById('line_primed').dispatchEvent(new Event('change'));
                        document.getElementById('prime_fluid').value = c.prime_fluid;
                        document.getElementById('dead_volume_ml').value = c.dead_volume_ml;
                    }

                    // Limpiar eventos transoperatorios viejos para iniciar de cero el duplicado
                    activeCaseId = null;
                    ketamineEvents = [];
                    renderKetamineEvents();
                    
                    // Desplazar vista hacia arriba
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                    
                } catch (error) {
                    console.error('Error cargando plantilla de caso:', error);
                }
            });
        });

        // 2. Exportar JSON a PartenVet
        document.querySelectorAll('.btn-export-parten').forEach(btn => {
            btn.addEventListener('click', async () => {
                const caseId = btn.getAttribute('data-id');
                try {
                    const res = await fetch(`/api/cases/${caseId}/export`);
                    const payload = await res.json();
                    
                    // Simular descarga de exportación
                    const filename = `partenvet_case_${caseId}.json`;
                    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    a.click();
                    
                    await loadHistoryAndDashboard();
                } catch (error) {
                    console.error('Error al exportar caso:', error);
                }
            });
        });

        // 3. Eliminar caso del historial
        document.querySelectorAll('.btn-delete-case').forEach(btn => {
            btn.addEventListener('click', async () => {
                const caseId = btn.getAttribute('data-id');
                if (confirm('¿Está seguro de que desea eliminar este procedimiento de forma permanente del historial? Esta acción es irreversible.')) {
                    try {
                        const res = await fetch(`/api/cases/${caseId}/delete`, { method: 'POST' });
                        const result = await res.json();
                        alert(result.message);
                        await loadHistoryAndDashboard();
                        await loadAuditTerminal();
                    } catch (error) {
                        console.error('Error al eliminar caso clínico:', error);
                    }
                }
            });
        });

        // 4. Generar Reporte PDF
        document.querySelectorAll('.btn-print-pdf').forEach(btn => {
            btn.addEventListener('click', () => {
                const caseId = btn.getAttribute('data-id');
                generateClinicalPDF(caseId);
            });
        });
    }

    // ==========================================
    // GENERACIÓN DE INFORME PDF QUIRÚRGICO (jsPDF)
    // ==========================================
    const btnGeneratePDF = document.getElementById('btn-generate-pdf');
    if (btnGeneratePDF) {
        btnGeneratePDF.addEventListener('click', () => {
            if (activeCaseId) {
                generateClinicalPDF(activeCaseId);
            } else {
                alert('Guarde el procedimiento clínico primero antes de generar el informe PDF.');
            }
        });
    }

    async function generateClinicalPDF(caseId) {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        
        try {
            const res = await fetch(`/api/cases/${caseId}`);
            const c = await res.json();
            
            // 1. TÍTULO Y DISEÑO DE CABECERA
            doc.setFillColor(15, 23, 42); // Fondo Slate oscuro
            doc.rect(0, 0, 210, 40, 'F');
            
            doc.setFont("Outfit", "bold");
            doc.setFontSize(22);
            doc.setTextColor(13, 148, 136); // Teal
            doc.text("SafeAnesthesia", 15, 18);
            
            doc.setFont("Inter", "normal");
            doc.setFontSize(10);
            doc.setTextColor(248, 250, 252);
            doc.text("Módulo de Infusión Volumétrica y Auditoría Anestésica", 15, 25);
            doc.text(`Fecha del Reporte: ${c.date} | Caso Clínico ID: #${c.id}`, 15, 31);
            
            // 2. DATOS DEL PACIENTE
            doc.setTextColor(15, 23, 42);
            doc.setFontSize(14);
            doc.setFont("Outfit", "bold");
            doc.text("1. Resumen y Datos del Paciente", 15, 50);
            doc.line(15, 52, 195, 52);
            
            doc.setFont("Inter", "normal");
            doc.setFontSize(10);
            doc.text(`Paciente: ${c.patient_name}`, 15, 60);
            doc.text(`Especie: ${c.species === 'dog' ? 'Perro (Canino)' : 'Gato (Felino)'}`, 15, 66);
            doc.text(`Raza: ${c.breed || 'Sin registro'}`, 15, 72);
            doc.text(`Peso Corporal: ${c.weight} kg`, 15, 78);
            doc.text(`Edad: ${c.age || 'Sin registro'}`, 100, 60);
            doc.text(`Clasificación ASA: ASA ${c.asa_class}`, 100, 66);
            doc.text(`Cirugía: ${c.surgery_type.toUpperCase()}`, 100, 72);
            doc.text(`Duración Estimada: ${c.duration_estimated} min`, 100, 78);
            
            // 3. DOSIFICACIÓN DE PROPONENTE
            doc.setFontSize(14);
            doc.setFont("Outfit", "bold");
            doc.text("2. Planificación y Cálculos de Propofol", 15, 92);
            doc.line(15, 94, 195, 94);
            
            doc.setFont("Inter", "normal");
            doc.setFontSize(10);
            doc.text(`Modalidad Utilizada: ${c.calculation_mode === 'infusomat' ? 'Programación Infusomat (Mezcla)' : 'Cálculo de Mantenimiento Puro'}`, 15, 102);
            doc.text(`Dosis Objetivo Programada: ${c.target_dose} mg/kg/min`, 15, 108);
            doc.text(`Concentración Comercial: Propofol ${c.propofol_concentration}`, 15, 114);
            doc.text(`Demanda de Propofol: ${c.total_propofol_mg} mg (${c.propofol_concentration === '1%' ? c.total_propofol_mg / 10 : c.total_propofol_mg / 20} ml comerciales extraídos)`, 15, 120);

            let nextY = 128;
            if (c.calculation_mode === 'infusomat') {
                doc.text(`Diluyente NaCl 0,9%: ${c.diluent_volume} ml`, 15, 128);
                doc.text(`Volumen Total Mezcla: ${c.final_mixture_volume} ml`, 15, 134);
                doc.text(`Concentración Final de la Mezcla: ${c.final_concentration} mg/ml`, 15, 140);
                doc.text(`Programación de FLOW en Bomba: ${c.flow_ml_h} ml/h`, 100, 128);
                doc.text(`Programación de VTBI en Bomba: ${c.vtbi_ml} ml`, 100, 134);
                doc.text(`Cebado de línea: ${c.line_primed === 'yes' ? 'Sí (con ' + c.prime_fluid + ')' : 'No'}`, 100, 140);
                nextY = 148;
            }

            // 4. REGISTRO TRANSQUIRÚRGICO (KETAMINA / LIDOCAÍNA)
            doc.setFontSize(14);
            doc.setFont("Outfit", "bold");
            doc.text("3. Control de Fármacos Transquirúrgicos", 15, nextY);
            doc.line(15, nextY + 2, 195, nextY + 2);
            
            doc.setFont("Inter", "normal");
            doc.setFontSize(10);
            
            // Lidocaína
            const l = c.lidocaine_event;
            if (l) {
                doc.text(`Lidocaína Infiltrada Local por Planos:`, 15, nextY + 10);
                doc.text(`• Línea Alba: ${l.linea_alba_ml} ml  |  • Ligamentos: ${l.ligamento_ml} ml  |  • Peritoneal: ${l.peritoneal_ml} ml  |  • Piel: ${l.piel_ml} ml`, 15, nextY + 16);
                doc.text(`Total de Lidocaína Administrada: ${l.total_mg} mg (${l.percentage_of_max}% de la dosis de toxicidad segura)`, 15, nextY + 22);
            }
            
            // Ketamina
            doc.text(`Línea de Tiempo de Refuerzos de Ketamina Bolo:`, 100, nextY + 10);
            if (c.ketamine_events.length === 0) {
                doc.text("No se registraron refuerzos de ketamina.", 100, nextY + 16);
            } else {
                let kY = nextY + 16;
                c.ketamine_events.forEach(k => {
                    doc.text(`• ${k.time_registered} - ${k.dose_mg_kg} mg/kg (${k.volume_ml} ml) por ${k.reason}`, 100, kY);
                    kY += 6;
                });
            }
            
            nextY = nextY + 36;

            // 5. REGISTRO FISIOLÓGICO OPCIONAL
            doc.setFontSize(14);
            doc.setFont("Outfit", "bold");
            doc.text("4. Parámetros de Monitorización Fisiológica", 15, nextY);
            doc.line(15, nextY + 2, 195, nextY + 2);
            
            doc.setFont("Inter", "normal");
            doc.setFontSize(10);
            doc.text(`FC: ${c.fc || '--'} lpm  |  FR: ${c.fr || '--'} rpm  |  SpO2: ${c.spo2 || '--'}%  |  Temp: ${c.temp || '--'} °C`, 15, nextY + 10);
            doc.text(`Presión Arterial: PAS ${c.pas || '--'} mmHg  /  PAM ${c.pam || '--'} mmHg  |  ETCO2: ${c.etco2 || '--'} mmHg`, 15, nextY + 16);
            
            nextY = nextY + 28;

            // 6. RESULTADOS REALES E INFORME
            doc.setFontSize(14);
            doc.setFont("Outfit", "bold");
            doc.text("5. Auditoría de Resultados Reales Anestésicos", 15, nextY);
            doc.line(15, nextY + 2, 195, nextY + 2);
            
            doc.setFont("Inter", "normal");
            doc.setFontSize(10);
            doc.text(`Duración Real Cirugía: ${c.duration_real || '--'} minutos`, 15, nextY + 10);
            doc.text(`Volumen Mezcla Real Infundido: ${c.actual_volume_infused || '--'} ml`, 15, nextY + 16);
            doc.text(`Propofol Real Administrado: ${c.actual_propofol_mg ? c.actual_propofol_mg.toFixed(2) + ' mg' : '--'} (${c.actual_mg_kg ? c.actual_mg_kg.toFixed(2) + ' mg/kg' : '--'})`, 15, nextY + 22);
            
            doc.setFillColor(241, 245, 249);
            doc.rect(100, nextY + 6, 95, 20, 'F');
            doc.setFont("Inter", "bold");
            doc.text("VELOCIDAD MEDIA REAL RECIBIDA:", 102, nextY + 12);
            doc.setTextColor(13, 148, 136); // Teal
            doc.setFontSize(12);
            doc.text(`${c.actual_avg_dose_rate ? c.actual_avg_dose_rate.toFixed(3) + ' mg/kg/min' : '-- mg/kg/min'}`, 102, nextY + 20);
            
            doc.setTextColor(15, 23, 42);
            doc.setFont("Inter", "normal");
            doc.setFontSize(9);
            doc.text(`Notas Quirúrgicas: ${c.notes || 'Ninguna observación registrada.'}`, 15, nextY + 32);
            
            // Firmas y disclaimer
            doc.line(15, nextY + 48, 85, nextY + 48);
            doc.text("Firma Médico Veterinario Anestesista", 15, nextY + 52);
            
            doc.setFontSize(7);
            doc.setTextColor(148, 163, 184);
            doc.text("Disclaimer: SafeAnesthesia es un sistema de soporte y auditoría matemática clínica, cuya aplicación y monitorización final es de absoluta responsabilidad del anestesiólogo veterinario.", 15, 285);
            
            doc.save(`safeanesthesia_case_report_${caseId}.pdf`);
            write_audit(current_user.id, 'pdf_generated', {'id': caseId});

        } catch (error) {
            console.error('Error al generar informe PDF:', error);
            alert('Error generando PDF de reporte.');
        }
    }

    // ==========================================
    // TRAZABILIDAD Y AUDITORÍA
    // ==========================================
    async function loadAuditTerminal() {
        const terminal = document.getElementById('audit-log-terminal');
        if (!terminal) return;
        
        try {
            const res = await fetch('/api/audit-logs');
            const logs = await res.json();
            
            terminal.innerHTML = '';
            logs.forEach(l => {
                const div = document.createElement('div');
                div.className = 'log-line';
                div.innerText = `[${l.timestamp}] IP:${l.ip_address} ACTION:${l.action} DETAILS:${l.details}`;
                terminal.appendChild(div);
            });
        } catch (error) {
            console.error('Error cargando bitácora de auditoría:', error);
        }
    }

    // ==========================================
    // CONTROL DE RESPALDOS JSON
    // ==========================================
    const backupFileInput = document.getElementById('backup_file');
    if (backupFileInput) {
        backupFileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            
            const btnLabel = document.querySelector('label[for="backup_file"]');
            const originalText = btnLabel.innerText;
            btnLabel.innerText = "Restaurando...";
            
            try {
                const res = await fetch('/api/backup/import', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await res.json();
                alert(result.message);
                if (res.ok && result.success) {
                    await loadHistoryAndDashboard();
                    await loadAuditTerminal();
                }
            } catch (error) {
                console.error('Error al importar backup JSON:', error);
            } finally {
                btnLabel.innerText = originalText;
                backupFileInput.value = ''; // reset
            }
        });
    }

    // ==========================================
    // MODO DESARROLLO (POBLAMIENTO DE TESTEO)
    // ==========================================
    const btnDevPopulate = document.getElementById('btn-dev-populate');
    if (btnDevPopulate) {
        btnDevPopulate.addEventListener('click', async () => {
            if (confirm('Esta acción borrará el historial actual y generará 10 cirugías simuladas en el historial con eventos y dosis precalculadas para testeo del sistema. ¿Desea continuar?')) {
                btnDevPopulate.disabled = true;
                btnDevPopulate.innerText = "Poblando base...";
                
                try {
                    const res = await fetch('/api/dev/populate', { method: 'POST' });
                    const result = await res.json();
                    alert(result.message);
                    
                    if (res.ok && result.success) {
                        await loadHistoryAndDashboard();
                        await loadAuditTerminal();
                    }
                } catch (error) {
                    console.error('Error poblando base de datos ficticia:', error);
                } finally {
                    btnDevPopulate.disabled = false;
                    btnDevPopulate.innerText = "Modo Dev: Generar Datos Simulación";
                }
            }
        });
    }

    // ==========================================
    // MODAL DE CAMBIO DE CONTRASEÑA
    // ==========================================
    const btnOpenPasswordModal = document.getElementById('btn-change-password-modal');
    const btnClosePasswordModal = document.getElementById('btn-close-password-modal');
    const passwordModal = document.getElementById('password-modal');
    const btnSaveNewPassword = document.getElementById('btn-save-new-password');

    if (btnOpenPasswordModal && passwordModal) {
        btnOpenPasswordModal.addEventListener('click', () => {
            passwordModal.classList.remove('hidden');
        });
    }

    if (btnClosePasswordModal && passwordModal) {
        btnClosePasswordModal.addEventListener('click', () => {
            passwordModal.classList.add('hidden');
            // Limpiar inputs
            document.getElementById('old_password').value = '';
            document.getElementById('new_password').value = '';
        });
    }

    if (btnSaveNewPassword) {
        btnSaveNewPassword.addEventListener('click', async () => {
            const oldPw = document.getElementById('old_password').value;
            const newPw = document.getElementById('new_password').value;
            
            if (!oldPw || !newPw) {
                alert('Por favor complete ambos campos.');
                return;
            }

            const payload = { old_password: oldPw, new_password: newPw };

            try {
                const res = await fetch('/change-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const result = await res.json();
                alert(result.message);
                
                if (res.ok && result.success) {
                    passwordModal.classList.add('hidden');
                    document.getElementById('old_password').value = '';
                    document.getElementById('new_password').value = '';
                    await loadAuditTerminal();
                }
            } catch (error) {
                console.error('Error al cambiar contraseña:', error);
            }
        });
    }
});
