document.addEventListener('DOMContentLoaded', () => {

    const btnCalc = document.getElementById('btn-calculate');
    
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
        updatePrintSummary();
        window.print();
    });

    document.getElementById('btn-pdf').addEventListener('click', () => {
        updatePrintSummary();
        window.print(); // Browser handles printing/saving as PDF much better for this layout.
    });

});
