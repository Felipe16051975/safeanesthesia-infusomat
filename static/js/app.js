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
    const printPreq = document.getElementById('print-summary');
    const printHospital = document.getElementById('print-summary-hospital');

    function setActivePrint(mode) {
        if (mode === 'preq') {
            printPreq.classList.add('active-print');
            printHospital.classList.remove('active-print');
        } else {
            printHospital.classList.add('active-print');
            printPreq.classList.remove('active-print');
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

    
    // Cebado logic
    const primeVolumeSelect = document.getElementById('priming_volume');
    const customPrimeInput = document.getElementById('custom_priming_vol');
    primeVolumeSelect.addEventListener('change', () => {
        if (primeVolumeSelect.value === 'custom') {
            customPrimeInput.classList.remove('hidden');
        } else {
            customPrimeInput.classList.add('hidden');
        }
    });

    const primeFluidSelect = document.getElementById('prime_fluid');
    const warningSuero = document.getElementById('prime-warning-suero');
    const warningMezcla = document.getElementById('prime-warning-mezcla');

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
    ['weight', 'species', 'k_conc', 'k_dose', 'lido_conc', 'lido_max_dose', 'fluid_hours'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', () => {
                updateKetamineLidocaine();
                updateFluids();
            });
            el.addEventListener('change', () => {
                updateKetamineLidocaine();
                updateFluids();
            });
        }
    });

    function getDeadVolume() {
        if (primeVolumeSelect.value === 'custom') return parseFloat(customPrimeInput.value) || 0;
        return parseFloat(primeVolumeSelect.value);
    }

    btnCalc.addEventListener('click', async () => {
        btnCalc.disabled = true;
        btnCalc.innerText = "Calculando...";

        try {
            const w = parseFloat(document.getElementById('weight').value);
            const duration = parseFloat(document.getElementById('duration_estimated').value);
            const dose = parseFloat(document.getElementById('target_dose').value);
            const concSelect = document.getElementById('propofol_concentration').value; // 1% or 2%
            const diluent = parseFloat(document.getElementById('diluent_volume').value);
            const primed = document.getElementById('line_primed').value; // yes / no
            const primeFluid = document.getElementById('prime_fluid').value; // suero / mezcla
            const deadVol = getDeadVolume();

            if (isNaN(w) || isNaN(duration) || isNaN(dose) || isNaN(diluent)) {
                throw new Error("Complete todos los campos requeridos.");
            }

            // Llamada al backend
            const propPayload = {
                patient_name: document.getElementById('patient_name').value || 'Paciente',
                weight: w,
                target_dose: dose,
                duration_estimated: duration,
                species: document.getElementById('species').value,
                propofol_concentration: concSelect,
                asa_class: document.getElementById('asa_class').value || 'I'
            };

            const propRes = await fetch('/api/calculate/propofol', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(propPayload)
            });
            const propData = await propRes.json();
            if (propData.error) throw new Error(propData.error);

            const propMl = propData.required_ml;

            const pumpPayload = {
                propofol_ml: propMl,
                total_mg: propData.total_mg,
                diluent_volume: diluent,
                duration_estimated: duration,
                line_primed: primed,
                prime_fluid: primeFluid,
                dead_volume_ml: deadVol
            };

            const pumpRes = await fetch('/api/calculate/pump', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(pumpPayload)
            });
            const pumpData = await pumpRes.json();
            if (pumpData.error) throw new Error(pumpData.error);

            // Update UI Paso 2
            document.getElementById('prop-prep-text').innerText = `Extraer ${propMl.toFixed(2)} ml de propofol ${concSelect} y agregar a ${diluent} ml de NaCl 0,9%.`;
            document.getElementById('prop-mg').innerText = propData.total_mg.toFixed(2);
            document.getElementById('prop-ml').innerText = propMl.toFixed(2);
            document.getElementById('prop-final-vol').innerText = (propMl + diluent).toFixed(2);
            document.getElementById('prop-final-conc').innerText = pumpData.final_concentration_mg_ml.toFixed(2);
            document.getElementById('propofol-results').style.display = 'block';

            // Update Paso 3 warnings
            warningSuero.classList.add('hidden');
            warningMezcla.classList.add('hidden');
            if (primeFluid === 'suero') {
                document.getElementById('prime-delay').innerText = pumpData.delay_time_min.toFixed(1);
                warningSuero.classList.remove('hidden');
            } else if (primeFluid === 'mezcla') {
                warningMezcla.classList.remove('hidden');
            }

            // Override FLOW and VTBI on frontend
            const volFinal = propMl + diluent;
            const horas = duration / 60;
            const flow = volFinal / horas;
            const vtbi = volFinal;

            // Update Paso 4
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
            alert(e.message);
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

        // perro: 60 ml/kg/dia -> 2.5 ml/kg/h
        // gato: 40 ml/kg/dia -> 1.66 ml/kg/h
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

        document.getElementById('pr_prop_mg').innerText = document.getElementById('prop-mg').innerText || '--';
        document.getElementById('pr_prop_ml').innerText = document.getElementById('prop-ml').innerText || '--';
        document.getElementById('pr_nacl_ml').innerText = document.getElementById('diluent_volume').value || '--';
        document.getElementById('pr_final_vol').innerText = document.getElementById('prop-final-vol').innerText || '--';
        document.getElementById('pr_final_conc').innerText = document.getElementById('prop-final-conc').innerText || '--';

        document.getElementById('pr_lcd_flow').innerText = document.getElementById('lcd-flow-val').innerText || '--';
        document.getElementById('pr_lcd_vtbi').innerText = document.getElementById('lcd-vtbi-val').innerText || '--';
        document.getElementById('pr_lcd_time').innerText = document.getElementById('lcd-time-val').innerText || '--';

        const ketOpt = document.getElementById('ketamine_opt').value;
        if (ketOpt === 'no') {
            document.getElementById('pr_ket_opt').innerText = 'No usar ketamina';
            document.getElementById('pr_ket_details').style.display = 'none';
        } else {
            document.getElementById('pr_ket_opt').innerText = 'Calcular bolo separado';
            document.getElementById('pr_ket_details').style.display = 'block';
            const kResult = document.getElementById('k-result').innerText;
            const regex = /([\d.]+) mg = ([\d.]+) ml/;
            const match = kResult.match(regex);
            if (match) {
                document.getElementById('pr_ket_mg').innerText = match[1];
                document.getElementById('pr_ket_ml').innerText = match[2];
            } else {
                document.getElementById('pr_ket_mg').innerText = '--';
                document.getElementById('pr_ket_ml').innerText = '--';
            }
            document.getElementById('pr_ket_reason').innerText = document.getElementById('k_reason').value || '--';
        }

        const lidoResult = document.getElementById('lido-result').innerText;
        const lRegexMg = /([\d.]+) mg totales/;
        const lRegexMl = /([\d.]+) ml de lidocaína/;
        const m1 = lidoResult.match(lRegexMg);
        const m2 = lidoResult.match(lRegexMl);
        document.getElementById('pr_lido_mg').innerText = m1 ? m1[1] : '--';
        document.getElementById('pr_lido_ml').innerText = m2 ? m2[1] : '--';
        document.getElementById('pr_lido_dil').innerText = document.getElementById('lido-dilution').innerText || '--';

        document.getElementById('pr_fluid_flow').innerText = document.getElementById('fluid-flow').innerText || '--';
        document.getElementById('pr_fluid_vtbi').innerText = document.getElementById('fluid-vtbi').innerText || '--';
        document.getElementById('pr_fluid_time').innerText = document.getElementById('fluid-time').innerText || '--';
    }

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
