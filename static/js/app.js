document.addEventListener('DOMContentLoaded', () => {

    const btnCalc = document.getElementById('btn-calculate');
    
    // Mode Toggle Logic
    let currentMode = 'preq'; // 'preq' or 'hospital'
    const btnModePreq = document.getElementById('btn-mode-preq');
    const btnModeHospital = document.getElementById('btn-mode-hospital');
    const preqModeDiv = document.getElementById('pre-q-mode');
    const hospitalModeDiv = document.getElementById('hospital-mode');
    const titleSpan = document.getElementById('mode-title-span');
    const subtitleP = document.getElementById('mode-subtitle-p');
    const printPreq = document.getElementById('print-summary-preq');
    const printHospital = document.getElementById('print-summary-hospital');

    function setActivePrint(mode) {
        if (mode === 'preq') {
            if (printPreq) printPreq.classList.add('active-print');
            if (printHospital) printHospital.classList.remove('active-print');
        } else {
            if (printHospital) printHospital.classList.add('active-print');
            if (printPreq) printPreq.classList.remove('active-print');
        }
    }

    // Set initial state
    setActivePrint('preq');

    btnModePreq.addEventListener('click', () => {
        currentMode = 'preq';
        btnModePreq.className = 'btn btn-teal';
        btnModeHospital.className = 'btn btn-outline';
        preqModeDiv.style.display = 'block';
        hospitalModeDiv.style.display = 'none';
        titleSpan.innerText = 'Pre-Q';
        subtitleP.innerText = 'Planificación Pre-Quirúrgica Simplificada';
        setActivePrint('preq');
    });

    btnModeHospital.addEventListener('click', () => {
        currentMode = 'hospital';
        btnModeHospital.className = 'btn btn-teal';
        btnModePreq.className = 'btn btn-outline';
        preqModeDiv.style.display = 'none';
        hospitalModeDiv.style.display = 'block';
        titleSpan.innerText = 'Hospital / CRI';
        subtitleP.innerText = 'Cálculo de Fluidoterapia y CRI';
        setActivePrint('hospital');
    });

    
    // (prime_fluid, primeVolumeSelect, customPrimeInput are now hidden stubs - cebado eliminated from Pre-Q)

    // Ketamina logic
    const ketamineOpt = document.getElementById('ketamine_opt');
    const ketamineFields = document.getElementById('ketamine_fields');
    ketamineOpt.addEventListener('change', () => {
        if (ketamineOpt.value === 'bolo') {
            ketamineFields.classList.remove('hidden');
        } else {
            ketamineFields.classList.add('hidden');
        }
        updateKetamineLidocaine();
    });

    // Event listeners for live updates of K, Lido and Fluids
    // Reactive variables and selector elements
    const anesthesiaModeSelect = document.getElementById('anesthesia_mode');
    const ketofolMixtureFields = document.getElementById('ketofol_mixture_fields');
    const useRatioSelect = document.getElementById('use_ratio_1_2');
    const targetDoseInput = document.getElementById('target_dose');
    const propDoseUnitSelect = document.getElementById('propofol_dose_unit');
    const ketamineTargetDoseInput = document.getElementById('ketamine_target_dose');
    const ketamineDoseUnitSelect = document.getElementById('ketamine_dose_unit');
    const diluentVolumeInput = document.getElementById('diluent_volume');
    
    let userHasSelectedContainerManually = false;

    // Toggle mixture fields and sync manual/auto bolus options
    anesthesiaModeSelect.addEventListener('change', () => {
        const mode = anesthesiaModeSelect.value;
        if (mode === 'propofol_ketamine_mixture') {
            ketofolMixtureFields.classList.remove('hidden');
        } else {
            ketofolMixtureFields.classList.add('hidden');
        }

        // Sync with Paso 5 Ketamina bolo
        const ketOpt = document.getElementById('ketamine_opt');
        const ketFields = document.getElementById('ketamine_fields');
        if (mode === 'propofol_ketamine_bolo') {
            ketOpt.value = 'bolo';
            ketFields.classList.remove('hidden');
        } else {
            ketOpt.value = 'no';
            ketFields.classList.add('hidden');
        }
        
        updateVolumeGuardLabels();
        updateKetamineLidocaine();
    });

    // Auto-calculate 1:2 Ketofol ratio
    function updateRatioAndUnits() {
        const ratioInfoEl = document.getElementById('ratio-auto-info');
        if (useRatioSelect.value === 'yes') {
            const pDose = parseFloat(targetDoseInput.value) || 0;
            ketamineDoseUnitSelect.value = propDoseUnitSelect.value;
            ketamineTargetDoseInput.value = (pDose / 2.0).toFixed(3);
            ketamineTargetDoseInput.disabled = true;
            ketamineDoseUnitSelect.disabled = true;
            if (ratioInfoEl) ratioInfoEl.style.display = 'block';
        } else {
            ketamineTargetDoseInput.disabled = false;
            ketamineDoseUnitSelect.disabled = false;
            if (ratioInfoEl) ratioInfoEl.style.display = 'none';
        }
    }

    if (useRatioSelect) {
        useRatioSelect.addEventListener('change', updateRatioAndUnits);
    }
    if (targetDoseInput) {
        targetDoseInput.addEventListener('input', updateRatioAndUnits);
    }
    if (propDoseUnitSelect) {
        propDoseUnitSelect.addEventListener('change', updateRatioAndUnits);
    }

    // Container manual selection tracker
    document.querySelectorAll('input[name="container_type"]').forEach(radio => {
        radio.addEventListener('change', () => {
            userHasSelectedContainerManually = true;
        });
    });

    const ketamineConcSel = document.getElementById('ketamine_concentration');
    const ketamineConcCustom = document.getElementById('ketamine_concentration_custom');
    if (ketamineConcSel) {
        ketamineConcSel.addEventListener('change', () => {
            if (ketamineConcSel.value === 'custom') {
                ketamineConcCustom.classList.remove('hidden');
            } else {
                ketamineConcCustom.classList.add('hidden');
            }
            updateVolumeGuardLabels();
            updateKetamineLidocaine();
            updateFluids();
        });
    }
    if (ketamineConcCustom) {
        ketamineConcCustom.addEventListener('input', () => {
            updateVolumeGuardLabels();
            updateKetamineLidocaine();
            updateFluids();
        });
    }

    function getKetamineConcentration() {
        if (!ketamineConcSel) return 50.0;
        if (ketamineConcSel.value === 'custom') {
            return parseFloat(ketamineConcCustom.value) || 50.0;
        }
        return parseFloat(ketamineConcSel.value) || 50.0;
    }

    // Dynamic Volume Guard labels near NaCl
    function updateVolumeGuardLabels() {
        const w = parseFloat(document.getElementById('weight').value);
        const species = document.getElementById('species').value;
        const duration = parseFloat(document.getElementById('duration_estimated').value);

        if (isNaN(w) || w <= 0 || isNaN(duration) || duration <= 0) {
            document.getElementById('nacl-suggested').innerText = '--';
            document.getElementById('nacl-max-rec').innerText = '--';
            return;
        }

        // 60 ml/kg/day for dogs, 50 for cats
        const mlKgDay = species === 'dog' ? 60.0 : 50.0;
        const maintH = (mlKgDay * w) / 24.0;
        const maintPeriod = maintH * (duration / 60.0);

        document.getElementById('nacl-suggested').innerText = '40.0 ml';
        document.getElementById('nacl-max-rec').innerText = `${maintPeriod.toFixed(1)} ml`;

        // Estimate volume to suggest container in real-time
        // Propofol standard dose 0.2 mg/kg/min -> 12 mg/kg/h. At 1% = 1.2 ml/kg/h.
        const concSelect = document.getElementById('propofol_concentration').value;
        const concVal = concSelect === '2%' ? 20.0 : 10.0;
        const pDoseConverted = convertToMgKgMinLocal(parseFloat(targetDoseInput.value) || 0, propDoseUnitSelect.value);
        const pMg = w * pDoseConverted * duration;
        const pMl = pMg / concVal;
        
        let kMl = 0;
        if (anesthesiaModeSelect.value === 'propofol_ketamine_mixture') {
            const kConc = getKetamineConcentration();
            let kDose = parseFloat(ketamineTargetDoseInput.value) || 0;
            if (useRatioSelect.value === 'yes') {
                kDose = pDoseConverted / 2.0;
            } else {
                kDose = convertToMgKgMinLocal(kDose, ketamineDoseUnitSelect.value);
            }
            const kMg = w * kDose * duration;
            kMl = kConc > 0 ? kMg / kConc : 0;
        }

        const diluent = parseFloat(diluentVolumeInput.value) || 0;
        const estFinalVol = pMl + kMl + diluent;

        autoSuggestContainer(estFinalVol);
    }

    function convertToMgKgMinLocal(val, unit) {
        if (unit === 'mg/kg/h') return val / 60.0;
        if (unit === 'mcg/kg/min') return val / 1000.0;
        return val;
    }

    function autoSuggestContainer(volume) {
        if (userHasSelectedContainerManually) return;

        let value = 'jeringa_50_ml';
        let label = 'cap. mínima 50 ml';
        if (volume <= 20.0) {
            value = 'jeringa_20_ml';
            label = 'cap. mínima 20 ml';
        } else if (volume <= 50.0) {
            value = 'jeringa_50_ml';
            label = 'cap. mínima 50 ml';
        } else {
            value = 'bolsa_100_ml';
            label = 'cap. mínima 100 ml';
        }

        const radio = document.querySelector(`input[name="container_type"][value="${value}"]`);
        if (radio) {
            radio.checked = true;
        }
        document.getElementById('suggested-container-lbl').innerText = label;
    }

    // Listeners for live updates of labels and parameters
    ['weight', 'species', 'duration_estimated', 'target_dose', 'propofol_dose_unit', 'ketamine_concentration', 'ketamine_target_dose', 'ketamine_dose_unit', 'diluent_volume', 'k_conc', 'k_dose', 'lido_conc', 'lido_max_dose', 'fluid_hours'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', () => {
                updateVolumeGuardLabels();
                updateKetamineLidocaine();
                updateFluids();
            });
            el.addEventListener('change', () => {
                updateVolumeGuardLabels();
                updateKetamineLidocaine();
                updateFluids();
            });
        }
    });


    btnCalc.addEventListener('click', async () => {
        btnCalc.disabled = true;
        btnCalc.innerText = "Calculando...";

        try {
            const w = parseFloat(document.getElementById('weight').value);
            const duration = parseFloat(document.getElementById('duration_estimated').value);
            const dose = parseFloat(document.getElementById('target_dose').value);
            const concSelect = document.getElementById('propofol_concentration').value; // 1% or 2%
            const diluent = parseFloat(document.getElementById('diluent_volume').value);

            if (isNaN(w) || isNaN(duration) || isNaN(dose) || isNaN(diluent)) {
                throw new Error("Complete todos los campos requeridos.");
            }

            // Llamada al backend con todos los parámetros clínicos del diseño Pre-Q
            const propPayload = {
                patient_name: document.getElementById('patient_name').value || 'Paciente',
                weight: w,
                target_dose: dose,
                duration_estimated: duration,
                species: document.getElementById('species').value,
                propofol_concentration: concSelect,
                asa_class: document.getElementById('asa_class').value || 'I',
                anesthesia_mode: anesthesiaModeSelect.value,
                ketamine_concentration: getKetamineConcentration(),
                ketamine_target_dose: parseFloat(document.getElementById('ketamine_target_dose').value) || 0.1,
                use_ratio_1_2: useRatioSelect.value === 'yes',
                diluent_volume: diluent,
                container_type: document.querySelector('input[name="container_type"]:checked')?.value || 'jeringa_50_ml',
                propofol_dose_unit: propDoseUnitSelect.value,
                ketamine_dose_unit: ketamineDoseUnitSelect.value
            };

            const propRes = await fetch('/api/calculate/propofol', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(propPayload)
            });
            const propData = await propRes.json();
            if (propData.error) throw new Error(propData.error);

            // EVALUAR ESTADO VOLUME GUARD
            const vgAlert = document.getElementById('volume-guard-alert');
            const vgAlertTxt = document.getElementById('volume-guard-alert-text');
            const secInfo = document.getElementById('secondary-validation-info');
            const secInfoTxt = document.getElementById('secondary-validation-info-text');

            // Mostrar validación informativa secundaria en todos los casos
            secInfo.classList.remove('hidden');
            secInfoTxt.innerText = propData.maintenance_info_text;

            if (propData.volume_guard_status === 'BLOCKED') {
                // Estado Bloqueado: mostrar alerta roja brillante
                vgAlert.className = 'col-span-2 p-3 rounded';
                vgAlert.style.backgroundColor = '#ef4444';
                vgAlert.style.color = '#ffffff';
                vgAlert.classList.remove('hidden');
                vgAlertTxt.innerText = propData.volume_guard_message;

                // Bloquear Infusomat
                document.getElementById('lcd-pump-status').innerText = 'BLOCKED';
                document.getElementById('lcd-pump-status').className = 'color-danger';
                document.getElementById('lcd-flow-val').innerText = '--';
                document.getElementById('lcd-vtbi-val').innerText = '--';
                document.getElementById('lcd-time-val').innerHTML = '--:-- <small>hh:mm</small>';

                // Ocultar resultados de preparación
                document.getElementById('propofol-results').style.display = 'none';
                
                throw new Error(propData.volume_guard_message);
            } else if (propData.volume_guard_status === 'WARNING') {
                // Estado Precaución: mostrar alerta amarilla
                vgAlert.className = 'col-span-2 p-3 rounded';
                vgAlert.style.backgroundColor = '#eab308';
                vgAlert.style.color = '#0f172a';
                vgAlert.classList.remove('hidden');
                vgAlertTxt.innerText = propData.volume_guard_message;
            } else {
                // Estado Seguro
                vgAlert.classList.add('hidden');
            }

            // Advertencias clínicas dinámicas
            const warningsContainer = document.getElementById('clinical-warnings-container');
            const warningsList = document.getElementById('clinical-warnings-list');
            if (propData.ketofol_warnings && propData.ketofol_warnings.length > 0) {
                warningsList.innerHTML = '';
                propData.ketofol_warnings.forEach(warn => {
                    const li = document.createElement('li');
                    li.innerText = warn;
                    warningsList.appendChild(li);
                });
                warningsContainer.classList.remove('hidden');
            } else {
                warningsContainer.classList.add('hidden');
            }

            const propMl = propData.required_ml;

            // Pump payload: VTBI = volumen final, FLOW = volumen final / horas, TIME = duración
            // No dead volume, no priming adjustments
            const pumpPayload = {
                propofol_ml: propMl,
                total_mg: propData.total_mg,
                diluent_volume: diluent,
                duration_estimated: duration,
                line_primed: 'yes',
                prime_fluid: 'suero',
                dead_volume_ml: 0
            };

            const pumpRes = await fetch('/api/calculate/pump', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(pumpPayload)
            });
            const pumpData = await pumpRes.json();
            if (pumpData.error) throw new Error(pumpData.error);

            // Update UI Paso 2
            const cName = propData.selected_container === 'jeringa_20_ml' ? 'cap. mínima 20 ml' : 
                          (propData.selected_container === 'jeringa_50_ml' ? 'cap. mínima 50 ml' : 'cap. mínima 100 ml');
                          
            if (propData.anesthesia_mode === 'propofol_ketamine_mixture') {
                document.getElementById('prop-prep-text').innerText = `Extraer ${propMl.toFixed(2)} ml de propofol ${concSelect} + ${propData.ketamine_required_ml.toFixed(2)} ml de ketamina y agregar a ${diluent} ml de NaCl 0,9%.`;
                document.getElementById('li-ket-result').style.display = 'block';
                document.getElementById('li-ket-dose-result').style.display = 'block';
                document.getElementById('li-ket-conc-result').style.display = 'block';
                document.getElementById('ket-mg').innerText = propData.ketamine_total_mg.toFixed(2);
                document.getElementById('ket-ml').innerText = propData.ketamine_required_ml.toFixed(2);
                document.getElementById('ket-target-dose').innerText = propData.target_ketamine_mg_kg_min.toFixed(4);
                document.getElementById('ket-delivered-dose').innerText = propData.delivered_ketamine_mg_kg_min.toFixed(4);
                document.getElementById('ket-final-conc').innerText = propData.final_ketamine_concentration.toFixed(4);
            } else {
                document.getElementById('prop-prep-text').innerText = `Extraer ${propMl.toFixed(2)} ml de propofol ${concSelect} y agregar a ${diluent} ml de NaCl 0,9%.`;
                document.getElementById('li-ket-result').style.display = 'none';
                document.getElementById('li-ket-dose-result').style.display = 'none';
                document.getElementById('li-ket-conc-result').style.display = 'none';
            }

            document.getElementById('prop-mg').innerText = propData.total_mg.toFixed(2);
            document.getElementById('prop-ml').innerText = propMl.toFixed(2);
            document.getElementById('prop-target-dose').innerText = propData.target_propofol_mg_kg_min.toFixed(4);
            document.getElementById('prop-delivered-dose').innerText = propData.delivered_propofol_mg_kg_min.toFixed(4);
            document.getElementById('result-nacl-ml').innerText = diluent.toFixed(2);
            document.getElementById('prop-final-vol').innerText = propData.final_volume.toFixed(2);
            document.getElementById('prop-final-conc').innerText = propData.final_propofol_concentration.toFixed(4);
            document.getElementById('result-container-used').innerText = cName;
            
            const vgStatusLbl = document.getElementById('result-volume-guard-lbl');
            vgStatusLbl.innerText = propData.volume_guard_status;
            vgStatusLbl.className = 'font-bold ' + (propData.volume_guard_status === 'SAFE' ? 'text-teal' : 'color-yellow');

            document.getElementById('propofol-results').style.display = 'block';

            // (Cebado eliminado del flujo Pre-Q - no hay advertencias de cebado)

            // Override FLOW and VTBI on frontend
            const volFinal = propData.final_volume;
            const horas = duration / 60;
            const flow = volFinal / horas;
            const vtbi = volFinal;

            // Update Paso 4 simulator B. Braun
            document.getElementById('lcd-pump-status').innerText = 'RUNNING';
            document.getElementById('lcd-pump-status').className = 'color-teal';
            document.getElementById('lcd-flow-val').innerText = flow.toFixed(1);
            document.getElementById('lcd-vtbi-val').innerText = vtbi.toFixed(1);
            
            const hrs = Math.floor(duration / 60);
            const mins = Math.floor(duration % 60);
            document.getElementById('lcd-time-val').innerHTML = `${hrs.toString().padStart(2,'0')}:${mins.toString().padStart(2,'0')} <small>hh:mm</small>`;

            updateKetamineLidocaine();
            updateFluids();

        } catch (e) {
            // No alert for blocks since we display the nice UI message
            if (!e.message.includes("superior") && !e.message.includes("no están permitidas")) {
                alert(e.message);
            }
        } finally {
            btnCalc.disabled = false;
            btnCalc.innerText = "Calcular y Actualizar Bomba";
        }
    });

    function updateKetamineLidocaine() {
        const w = parseFloat(document.getElementById('weight').value);
        if (isNaN(w)) return;

        // Ketamina
        if (ketamineOpt.value === 'bolo') {
            const kConc = parseFloat(document.getElementById('k_conc').value);
            const kDose = parseFloat(document.getElementById('k_dose').value);
            if (!isNaN(kConc) && !isNaN(kDose) && kConc > 0) {
                const mg = w * kDose;
                const ml = mg / kConc;
                document.getElementById('k-result').innerText = `Bolo sugerido: ${mg.toFixed(2)} mg = ${ml.toFixed(2)} ml`;
            }
        }

        // Lidocaina
        const lConcPct = parseFloat(document.getElementById('lido_conc').value);
        const lMax = parseFloat(document.getElementById('lido_max_dose').value);
        if (!isNaN(lConcPct) && !isNaN(lMax)) {
            const maxMg = w * lMax;
            const concMgMl = lConcPct * 10;
            const maxMl = maxMg / concMgMl;
            document.getElementById('lido-result').innerText = `Para este paciente, no exceder ${maxMg.toFixed(2)} mg totales de lidocaína.\nEquivale a ${maxMl.toFixed(2)} ml de lidocaína comercial.`;
            document.getElementById('lido-dilution').innerText = `Puede diluirse hasta 3 ml con suero para repartir durante el procedimiento.`;
        }
    }

    function updateFluids() {
        const w = parseFloat(document.getElementById('weight').value);
        const species = document.getElementById('species').value;
        const hrs = parseInt(document.getElementById('fluid_hours').value);

        if (isNaN(w) || isNaN(hrs)) return;

        const mlKgDia = species === 'dog' ? 60 : 40;
        const rate = (w * mlKgDia) / 24;
        const vtbi = rate * hrs;

        document.getElementById('fluid-flow').innerText = rate.toFixed(1);
        document.getElementById('fluid-vtbi').innerText = vtbi.toFixed(1);
        document.getElementById('fluid-time').innerHTML = `${hrs.toString().padStart(2,'0')}:00 <small>hh:mm</small>`;
    }

    function updatePrintSummary() {
        document.getElementById('pr_name').innerText = document.getElementById('patient_name').value || '--';
        const speciesSel = document.getElementById('species');
        document.getElementById('pr_species').innerText = speciesSel.options[speciesSel.selectedIndex]?.text || '--';
        document.getElementById('pr_weight').innerText = document.getElementById('weight').value || '--';
        document.getElementById('pr_age').innerText = document.getElementById('age').value || '--';
        document.getElementById('pr_asa').innerText = document.getElementById('asa_class').value || '--';
        document.getElementById('pr_surgery').innerText = document.getElementById('surgery_type').value || '--';
        document.getElementById('pr_duration').innerText = document.getElementById('duration_estimated').value || '--';

        const modeLabel = anesthesiaModeSelect.options[anesthesiaModeSelect.selectedIndex]?.text || '--';
        document.getElementById('pr_anesthesia_mode').innerText = modeLabel;
        document.getElementById('pr_container_type').innerText = document.getElementById('result-container-used').innerText || '--';

        const propConcSel = document.getElementById('propofol_concentration');
        document.getElementById('pr_prop_conc').innerText = propConcSel.options[propConcSel.selectedIndex]?.text || '--';
        document.getElementById('pr_prop_dose').innerText = document.getElementById('target_dose').value + ' ' + document.getElementById('propofol_dose_unit').value;
        document.getElementById('pr_prop_mg').innerText = document.getElementById('prop-mg').innerText || '--';
        document.getElementById('pr_prop_ml').innerText = document.getElementById('prop-ml').innerText || '--';
        document.getElementById('pr_prep_prop').innerText = document.getElementById('prop-ml').innerText || '--';
        
        document.getElementById('pr_nacl_ml').innerText = document.getElementById('diluent_volume').value || '--';
        document.getElementById('pr_final_vol').innerText = document.getElementById('prop-final-vol').innerText || '--';

        // Ketamina Mezcla si corresponde
        const prKetMixRow = document.getElementById('pr_ket_mix_row');
        const prPrepKetRow = document.getElementById('pr_prep_ket_row');
        if (anesthesiaModeSelect.value === 'propofol_ketamine_mixture') {
            prKetMixRow.style.display = 'block';
            prPrepKetRow.style.display = 'block';
            const ketConcSel = document.getElementById('ketamine_concentration');
            let ketConcText = ketConcSel.options[ketConcSel.selectedIndex]?.text || '--';
            if (ketConcSel.value === 'custom') {
                ketConcText = document.getElementById('ketamine_concentration_custom').value + ' mg/ml';
            }
            document.getElementById('pr_ket_conc').innerText = ketConcText;
            document.getElementById('pr_ket_dose').innerText = document.getElementById('ketamine_target_dose').value + ' ' + document.getElementById('ketamine_dose_unit').value;
            document.getElementById('pr_ket_mix_mg').innerText = document.getElementById('ket-mg').innerText || '--';
            document.getElementById('pr_ket_mix_ml').innerText = document.getElementById('ket-ml').innerText || '--';
            document.getElementById('pr_prep_ket').innerText = document.getElementById('ket-ml').innerText || '--';
        } else {
            prKetMixRow.style.display = 'none';
            prPrepKetRow.style.display = 'none';
        }

        // Warnings
        const warningsContainer = document.getElementById('pr_warnings_container');
        const prVgWarning = document.getElementById('pr_vg_warning');
        const vgStatus = document.getElementById('result-volume-guard-lbl').innerText;
        document.getElementById('pr_volume_guard_status').innerText = vgStatus;
        
        let hasWarnings = false;
        if (vgStatus.includes("WARNING") || vgStatus.includes("BLOCKED")) {
            prVgWarning.style.display = 'block';
            hasWarnings = true;
        } else {
            prVgWarning.style.display = 'none';
        }

        const prWarnList = document.getElementById('pr_clinical_warnings_list');
        const activeWarnings = document.querySelectorAll('#clinical-warnings-list li');
        prWarnList.innerHTML = '';
        if (activeWarnings.length > 0) {
            activeWarnings.forEach(li => {
                const newLi = document.createElement('li');
                newLi.innerText = li.innerText;
                prWarnList.appendChild(newLi);
            });
            hasWarnings = true;
            prWarnList.style.display = 'block';
        } else {
            prWarnList.style.display = 'none';
        }
        
        if (hasWarnings) {
            warningsContainer.style.display = 'block';
        } else {
            warningsContainer.style.display = 'none';
        }

        document.getElementById('pr_lcd_flow').innerText = document.getElementById('lcd-flow-val').innerText || '--';
        document.getElementById('pr_lcd_vtbi').innerText = document.getElementById('lcd-vtbi-val').innerText || '--';
        document.getElementById('pr_lcd_time').innerText = document.getElementById('lcd-time-val').innerText || '--';
    }

    // Call dynamic labels update initially
    updateVolumeGuardLabels();
    updateRatioAndUnits();

    document.getElementById('btn-print').addEventListener('click', () => {
        if (currentMode === 'preq') {
            updatePrintSummary();
        } else {
            updateHospitalPrintSummary();
        }
        window.print();
    });

    document.getElementById('btn-pdf').addEventListener('click', () => {
        if (currentMode === 'preq') {
            updatePrintSummary();
        } else {
            updateHospitalPrintSummary();
        }
        window.print(); // Browser handles printing/saving as PDF much better for this layout.
    });

    // HOSPITAL / CRI LOGIC

    // Sync dehydration radio → estimated % input
    document.querySelectorAll('input[name="hosp_dehydration"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const estInput = document.getElementById('hosp_dehydration_estimated');
            if (estInput) estInput.value = radio.value;
        });
    });

    // Sync losses custom field toggle
    const hospLossesType = document.getElementById('hosp_losses_type');
    const hospLossesCustom = document.getElementById('hosp_losses_custom');
    hospLossesType.addEventListener('change', () => {
        if (hospLossesType.value === 'custom') {
            hospLossesCustom.classList.remove('hidden');
        } else {
            hospLossesCustom.classList.add('hidden');
        }
    });

    const hospFluidHours = document.getElementById('hosp_fluid_hours');
    const hospFluidHoursCustom = document.getElementById('hosp_fluid_hours_custom');
    hospFluidHours.addEventListener('change', () => {
        if (hospFluidHours.value === 'custom') {
            hospFluidHoursCustom.classList.remove('hidden');
        } else {
            hospFluidHoursCustom.classList.add('hidden');
        }
    });

    const btnCalcHosp = document.getElementById('btn-calculate-hosp');
    btnCalcHosp.addEventListener('click', async () => {
        btnCalcHosp.disabled = true;
        btnCalcHosp.innerText = 'Calculando...';

        try {
            // FLUIDS
            const w = parseFloat(document.getElementById('hosp_weight').value);
            if (isNaN(w)) throw new Error("Ingrese el peso del paciente.");

            const species = document.getElementById('hosp_species').value;
            // Dehydration selector (radio buttons)
            const dehyRadio = document.querySelector('input[name="hosp_dehydration"]:checked');
            const dehy = dehyRadio ? parseFloat(dehyRadio.value) : 0;
            // Losses selector
            const lossesSelect = document.getElementById('hosp_losses_type');
            let losses = 0;
            const lossesMap = {
              none: 0,
              vomitos_leve: 20,
              vomitos_moderado: 50,
              vomitos_severo: 100,
              diarrea_leve: 20,
              diarrea_moderada: 50,
              diarrea_severa: 100,
              vomitos_diarrea: 80,
              poliuria: 30,
              sangrado: 150,
              custom: 0
            };
            if (lossesSelect.value === 'custom') {
              losses = parseFloat(document.getElementById('hosp_losses_custom').value) || 0;
            } else {
              losses = lossesMap[lossesSelect.value] || 0;
            }
            
            let hours = 24;
            if (hospFluidHours.value === 'custom') {
                hours = parseFloat(hospFluidHoursCustom.value);
            } else {
                hours = parseFloat(hospFluidHours.value);
            }
            if (isNaN(hours) || hours <= 0) hours = 24;

            const fluidPayload = {
                weight: w,
                species: species,
                dehydration_pct: dehy,
                losses_ml: losses,
                replacement_hours: hours,
                patient_name: document.getElementById('hosp_patient_name').value
            };

            const fluidRes = await fetch('/api/calculate/hospital_fluids', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(fluidPayload)
            });
            const fluidData = await fluidRes.json();
            if (fluidData.error) throw new Error(fluidData.error);

            document.getElementById('hosp-maint-day').innerText = fluidData.maintenance_ml_day;
            document.getElementById('hosp-maint-h').innerText = fluidData.maintenance_ml_h;
            document.getElementById('hosp-deficit').innerText = fluidData.deficit_ml;
            document.getElementById('hosp-losses-res').innerText = fluidData.losses_ml;
            document.getElementById('hosp-total-vol').innerText = fluidData.total_volume_in_period;
            document.getElementById('hosp-fluid-results').style.display = 'block';

            document.getElementById('lcd-hosp-fluid-status').innerText = 'RUNNING';
            document.getElementById('lcd-hosp-fluid-status').className = 'color-teal';
            document.getElementById('lcd-hosp-fluid-flow').innerText = fluidData.flow_ml_h.toFixed(1);
            document.getElementById('lcd-hosp-fluid-vtbi').innerText = fluidData.vtbi_ml.toFixed(1);
            
            const fHrs = Math.floor(fluidData.time_h);
            const fMins = Math.round((fluidData.time_h - fHrs) * 60);
            document.getElementById('lcd-hosp-fluid-time').innerHTML = `${fHrs.toString().padStart(2,'0')}:${fMins.toString().padStart(2,'0')} <small>hh:mm</small>`;

            // CRI
            const criDose = parseFloat(document.getElementById('hosp_cri_dose').value);
            if (!isNaN(criDose) && criDose > 0) {
                const criPayload = {
                    weight: w,
                    dose: criDose,
                    unit: document.getElementById('hosp_cri_unit').value,
                    concentration_mg_ml: parseFloat(document.getElementById('hosp_cri_conc').value) || 0,
                    final_volume_ml: parseFloat(document.getElementById('hosp_cri_final_vol').value) || 0,
                    duration_hours: parseFloat(document.getElementById('hosp_cri_hours').value) || 24,
                    drug_name: document.getElementById('hosp_cri_drug').value
                };

                const criRes = await fetch('/api/calculate/hospital_cri', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(criPayload)
                });
                const criData = await criRes.json();
                if (criData.error) throw new Error(criData.error);

                document.getElementById('hosp-cri-text').innerText = `Extraer ${criData.drug_ml} ml de medicamento y agregarlo a ${criData.base_fluid_ml} ml de solución base.`;
                document.getElementById('hosp-cri-total-mg').innerText = criData.total_mg;
                document.getElementById('hosp-cri-drug-ml').innerText = criData.drug_ml;
                document.getElementById('hosp-cri-base-ml').innerText = criData.base_fluid_ml;
                document.getElementById('hosp-cri-final-conc').innerText = criData.final_concentration_mg_ml;
                document.getElementById('hosp-cri-results').style.display = 'block';

                document.getElementById('lcd-hosp-cri-status').innerText = 'RUNNING';
                document.getElementById('lcd-hosp-cri-status').className = 'color-teal';
                document.getElementById('lcd-hosp-cri-flow').innerText = criData.flow_ml_h.toFixed(1);
                document.getElementById('lcd-hosp-cri-vtbi').innerText = criData.vtbi_ml.toFixed(1);
                
                const cHrs = Math.floor(criData.time_h);
                const cMins = Math.round((criData.time_h - cHrs) * 60);
                document.getElementById('lcd-hosp-cri-time').innerHTML = `${cHrs.toString().padStart(2,'0')}:${cMins.toString().padStart(2,'0')} <small>hh:mm</small>`;
            } else {
                // Limpiar CRI si no hay dosis
                document.getElementById('hosp-cri-results').style.display = 'none';
                document.getElementById('lcd-hosp-cri-status').innerText = 'ESPERANDO CÁLCULO';
                document.getElementById('lcd-hosp-cri-status').className = 'color-yellow';
                document.getElementById('lcd-hosp-cri-flow').innerText = '--';
                document.getElementById('lcd-hosp-cri-vtbi').innerText = '--';
                document.getElementById('lcd-hosp-cri-time').innerHTML = '--:-- <small>hh:mm</small>';
            }

        } catch (e) {
            alert(e.message);
        } finally {
            btnCalcHosp.disabled = false;
            btnCalcHosp.innerText = 'Calcular Hospital / CRI';
        }
    });

    function updateHospitalPrintSummary() {
        document.getElementById('pr_hosp_name').innerText = document.getElementById('hosp_patient_name').value || '--';
        const spSel = document.getElementById('hosp_species');
        document.getElementById('pr_hosp_species').innerText = spSel.options[spSel.selectedIndex]?.text || '--';
        document.getElementById('pr_hosp_weight').innerText = document.getElementById('hosp_weight').value || '--';
        document.getElementById('pr_hosp_age').innerText = document.getElementById('hosp_age').value || '--';
        document.getElementById('pr_hosp_reason').innerText = document.getElementById('hosp_reason').value || '--';


        document.getElementById('pr_hosp_maint_day').innerText = document.getElementById('hosp-maint-day').innerText || '--';
        document.getElementById('pr_hosp_deficit').innerText = document.getElementById('hosp-deficit').innerText || '--';
        document.getElementById('pr_hosp_losses').innerText = document.getElementById('hosp-losses-res').innerText || '--';
        document.getElementById('pr_hosp_total_vol').innerText = document.getElementById('hosp-total-vol').innerText || '--';

        document.getElementById('pr_hosp_lcd_fluid_flow').innerText = document.getElementById('lcd-hosp-fluid-flow').innerText || '--';
        document.getElementById('pr_hosp_lcd_fluid_vtbi').innerText = document.getElementById('lcd-hosp-fluid-vtbi').innerText || '--';
        document.getElementById('pr_hosp_lcd_fluid_time').innerText = document.getElementById('lcd-hosp-fluid-time').innerText || '--';

        document.getElementById('pr_hosp_cri_drug').innerText = document.getElementById('hosp_cri_drug').value || '--';
        document.getElementById('pr_hosp_cri_dose').innerText = document.getElementById('hosp_cri_dose').value ? `${document.getElementById('hosp_cri_dose').value} ${document.getElementById('hosp_cri_unit').value}` : '--';
        document.getElementById('pr_hosp_cri_drug_ml').innerText = document.getElementById('hosp-cri-drug-ml').innerText || '--';
        document.getElementById('pr_hosp_cri_base_ml').innerText = document.getElementById('hosp-cri-base-ml').innerText || '--';
        document.getElementById('pr_hosp_cri_final_vol').innerText = document.getElementById('hosp_cri_final_vol').value || '--';

        document.getElementById('pr_hosp_lcd_cri_flow').innerText = document.getElementById('lcd-hosp-cri-flow').innerText || '--';
        document.getElementById('pr_hosp_lcd_cri_vtbi').innerText = document.getElementById('lcd-hosp-cri-vtbi').innerText || '--';
        document.getElementById('pr_hosp_lcd_cri_time').innerText = document.getElementById('lcd-hosp-cri-time').innerText || '--';
    }

});
