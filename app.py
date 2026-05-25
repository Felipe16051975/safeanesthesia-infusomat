import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt

# Carga de Modelos y Servicios
from models import db, User, AnesthesiaCase, KetamineEvent, LidocaineEvent, AuditLog
from services.propofol_service import calculate_propofol
from services.pump_service import calculate_pump
from services.ketamine_service import calculate_ketamine_reinforcement
from services.lidocaine_service import evaluate_lidocaine_use
from services.hospital_fluids_service import calculate_fluid_therapy
from services.hospital_cri_service import build_cri

app = Flask(__name__)
app.config['SECRET_KEY'] = 'safeanesthesia-partenvet-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Habilitar cookies HttpOnly y SameSite por defecto
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def write_audit(user_id, action, details):
    """Registra una acción en la bitácora de auditoría de la base de datos."""
    try:
        ip = request.remote_addr
        log = AuditLog(
            user_id=user_id,
            action=action,
            details=json.dumps(details, ensure_ascii=False) if isinstance(details, dict) else str(details),
            ip_address=ip
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Error escribiendo bitácora de auditoría: {e}")

# ==========================================
# RUTAS DE AUTENTICACIÓN
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        # Permite envío por JSON (AJAX) o Formulario estándar
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        remember = True if data.get('remember') in [True, 'on', 'true'] else False
        
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            write_audit(user.id, 'login', {'username': username, 'status': 'success'})
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Acceso exitoso.'})
            return redirect(url_for('index'))
            
        write_audit(None, 'login_failed', {'username': username, 'status': 'failed'})
        if request.is_json:
            return jsonify({'success': False, 'message': 'Usuario o contraseña inválidos.'}), 401
        return render_template('login.html', error='Credenciales inválidas.')
        
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    uid = current_user.id
    uname = current_user.username
    logout_user()
    write_audit(uid, 'logout', {'username': uname})
    return redirect(url_for('login'))

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    old_pw = data.get('old_password')
    new_pw = data.get('new_password')
    
    if not old_pw or not new_pw:
        return jsonify({'success': False, 'message': 'Faltan parámetros requeridos.'}), 400
        
    if bcrypt.check_password_hash(current_user.password_hash, old_pw):
        current_user.password_hash = bcrypt.generate_password_hash(new_pw).decode('utf-8')
        db.session.commit()
        write_audit(current_user.id, 'change_password', {'status': 'success'})
        return jsonify({'success': True, 'message': 'Contraseña cambiada con éxito.'})
        
    write_audit(current_user.id, 'change_password_failed', {'reason': 'old password incorrect'})
    return jsonify({'success': False, 'message': 'La contraseña actual es incorrecta.'}), 400

# ==========================================
# VISTAS PRINCIPALES
# ==========================================

@app.route('/')
@login_required
def index():
    return render_template('index.html', debug=app.debug)

# ==========================================
# API DE CONFIGURACIÓN Y LÍMITES
# ==========================================

@app.route('/api/limits', methods=['GET'])
@login_required
def get_limits():
    """Lee y consolida las configuraciones JSON en la carpeta config."""
    config_dir = os.path.join(app.root_path, 'config')
    files = {
        'propofol': 'propofol_limits.json',
        'ketamine': 'ketamine_limits.json',
        'lidocaine': 'lidocaine_limits.json',
        'surgeries': 'surgery_profiles.json'
    }
    
    consolidated = {}
    for key, filename in files.items():
        path = os.path.join(config_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                consolidated[key] = json.load(f)
        except Exception as e:
            consolidated[key] = {'error': f'No se pudo cargar: {str(e)}'}
            
    return jsonify(consolidated)

@app.route('/api/limits/update', methods=['POST'])
@login_required
def update_limits():
    """Permite al veterinario actualizar los parámetros clínicos JSON guardando versionado."""
    data = request.get_json()
    config_key = data.get('key') # 'propofol', 'ketamine', 'lidocaine', 'surgeries'
    new_limits = data.get('limits')
    reviewer = data.get('reviewed_by', 'Dr. Felipe Inostroza')
    
    if config_key not in ['propofol', 'ketamine', 'lidocaine', 'surgeries']:
        return jsonify({'success': False, 'message': 'Llave de configuración inválida.'}), 400
        
    files = {
        'propofol': 'propofol_limits.json',
        'ketamine': 'ketamine_limits.json',
        'lidocaine': 'lidocaine_limits.json',
        'surgeries': 'surgery_profiles.json'
    }
    
    path = os.path.join(app.root_path, 'config', files[config_key])
    try:
        # Cargar archivo actual para incrementar versión
        with open(path, 'r', encoding='utf-8') as f:
            current_data = json.load(f)
            
        old_meta = current_data.get('_metadata', {})
        try:
            new_version = str(round(float(old_meta.get('version', '1.0')) + 0.1, 1))
        except ValueError:
            new_version = "1.1"
            
        # Armar nueva estructura
        updated_structure = {
            "_metadata": {
                "version": new_version,
                "last_review": datetime.utcnow().strftime('%Y-%m-%d'),
                "reviewed_by": reviewer,
                "clinical_notes": old_meta.get('clinical_notes', 'Valores configurables editables.')
            }
        }
        
        # Guardar según el tipo
        if config_key == 'surgeries':
            updated_structure['profiles'] = new_limits
        else:
            updated_structure['limits'] = new_limits
            
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(updated_structure, f, indent=2, ensure_ascii=False)
            
        write_audit(current_user.id, 'limits_updated', {'key': config_key, 'version': new_version})
        return jsonify({'success': True, 'message': 'Configuración actualizada y versionada.', 'version': new_version})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al guardar límites: {str(e)}'}), 500

# ==========================================
# CAPA DE SERVICIOS - CALCULOS API
# ==========================================

@app.route('/api/calculate/propofol', methods=['POST'])
@login_required
def api_calc_propofol():
    data = request.get_json()
    try:
        weight = float(data.get('weight', 0))
        target_dose = float(data.get('target_dose', 0))
        duration = float(data.get('duration_estimated', 0))
        species = data.get('species')
        propofol_pct = data.get('propofol_concentration', '1%')
        asa = data.get('asa_class', 'I')
        
        # Nuevos parámetros del diseño clínico
        anesthesia_mode = data.get('anesthesia_mode', 'propofol_solo')
        ketamine_concentration = float(data.get('ketamine_concentration', 50.0))
        ketamine_target_dose = float(data.get('ketamine_target_dose', 0.1))
        use_ratio_1_2 = data.get('use_ratio_1_2', False)
        diluent_volume = float(data.get('diluent_volume', 40.0))
        container_type = data.get('container_type')
        propofol_dose_unit = data.get('propofol_dose_unit', 'mg/kg/min')
        ketamine_dose_unit = data.get('ketamine_dose_unit', 'mg/kg/min')
        
        results = calculate_propofol(
            weight=weight,
            target_dose=target_dose,
            duration_min=duration,
            species=species,
            propofol_pct=propofol_pct,
            asa_class=asa,
            anesthesia_mode=anesthesia_mode,
            ketamine_concentration=ketamine_concentration,
            ketamine_target_dose=ketamine_target_dose,
            use_ratio_1_2=use_ratio_1_2,
            diluent_volume=diluent_volume,
            container_type=container_type,
            propofol_dose_unit=propofol_dose_unit,
            ketamine_dose_unit=ketamine_dose_unit
        )
        write_audit(current_user.id, 'calculation_generated', {'patient': data.get('patient_name'), 'species': species})
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/calculate/pump', methods=['POST'])
@login_required
def api_calc_pump():
    data = request.get_json()
    try:
        propofol_ml = float(data.get('propofol_ml', 0))
        total_mg = float(data.get('total_mg', 0))
        diluent_ml = float(data.get('diluent_volume', 0))
        duration = float(data.get('duration_estimated', 0))
        line_primed = data.get('line_primed', 'no')
        prime_fluid = data.get('prime_fluid', 'suero')
        dead_volume = float(data.get('dead_volume_ml', 15.0))
        
        results = calculate_pump(propofol_ml, total_mg, diluent_ml, duration, line_primed, prime_fluid, dead_volume)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/calculate/ketamine', methods=['POST'])
@login_required
def api_calc_ketamine():
    data = request.get_json()
    try:
        weight = float(data.get('weight', 0))
        dose_mg_kg = float(data.get('target_dose_mg_kg', 0.5))
        concentration = data.get('concentration_mg_ml')
        if concentration is not None:
            concentration = float(concentration)
            
        results = calculate_ketamine_reinforcement(weight, dose_mg_kg, concentration)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/calculate/lidocaine', methods=['POST'])
@login_required
def api_calc_lidocaine():
    data = request.get_json()
    try:
        weight = float(data.get('weight', 0))
        species = data.get('species')
        concentration_pct = float(data.get('concentration_pct', 2.0))
        linea_alba = float(data.get('linea_alba_ml', 0))
        ligamento = float(data.get('ligamento_ml', 0))
        peritoneal = float(data.get('peritoneal_ml', 0))
        piel = float(data.get('piel_ml', 0))
        
        results = evaluate_lidocaine_use(weight, species, concentration_pct, linea_alba, ligamento, peritoneal, piel)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/calculate/hospital_fluids', methods=['POST'])
@login_required
def api_calc_hospital_fluids():
    data = request.get_json()
    try:
        weight = float(data.get('weight', 0))
        dehydration_pct = float(data.get('dehydration_pct', 0))
        losses_ml = float(data.get('losses_ml', 0))
        replacement_hours = float(data.get('replacement_hours', 24))
        main_problem = data.get('main_problem', 'Otro')
        renal_state = data.get('renal_state', 'Normal')
        hepatic_state = data.get('hepatic_state', 'Normal')
        
        results = calculate_fluid_therapy(
            weight, dehydration_pct, losses_ml,
            main_problem, renal_state, hepatic_state, replacement_hours
        )
        write_audit(current_user.id, 'hospital_fluids_calculated', {'patient': data.get('patient_name')})
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/calculate/hospital_cri', methods=['POST'])
@login_required
def api_calc_hospital_cri():
    data = request.get_json()
    try:
        drugs_input = data.get('drugs', [])
        bag_volume_ml = float(data.get('bag_volume_ml', 0))
        species = data.get('species', 'dog')
        
        results = build_cri(drugs_input, bag_volume_ml, species)
        write_audit(current_user.id, 'hospital_cri_calculated', {'drugs': len(drugs_input)})
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ==========================================
# HISTORIAL DE CASOS (API CRUD)
# ==========================================

@app.route('/api/cases', methods=['GET'])
@login_required
def get_cases():
    """Devuelve la lista de casos guardados en el historial."""
    cases = AnesthesiaCase.query.order_by(AnesthesiaCase.id.desc()).all()
    out = []
    for c in cases:
        out.append({
            'id': c.id,
            'date': c.date,
            'patient_name': c.patient_name,
            'species': c.species,
            'breed': c.breed,
            'weight': c.weight,
            'asa_class': c.asa_class,
            'surgery_type': c.surgery_type,
            'duration_real': c.duration_real,
            'actual_volume_infused': c.actual_volume_infused,
            'actual_avg_dose_rate': c.actual_avg_dose_rate,
            'exported': c.exported
        })
    return jsonify(out)

@app.route('/api/cases/save', methods=['POST'])
@login_required
def save_case():
    """Crea o actualiza un caso relacionalmente en SQLite."""
    data = request.get_json()
    try:
        case_id = data.get('id')
        if case_id:
            c = AnesthesiaCase.query.get(case_id)
            if not c:
                return jsonify({'success': False, 'message': 'Caso no encontrado.'}), 404
            # Eliminar eventos viejos para volver a guardar
            KetamineEvent.query.filter_by(case_id=c.id).delete()
            if c.lidocaine_event:
                db.session.delete(c.lidocaine_event)
        else:
            c = AnesthesiaCase()
            db.session.add(c)
            
        # Llenar datos del paciente
        c.patient_name = data.get('patient_name')
        c.species = data.get('species')
        c.breed = data.get('breed')
        c.weight = float(data.get('weight', 0))
        c.age = data.get('age')
        c.asa_class = data.get('asa_class')
        c.surgery_type = data.get('surgery_type')
        c.duration_estimated = float(data.get('duration_estimated', 0))
        c.duration_real = float(data.get('duration_real', 0)) if data.get('duration_real') else None
        c.calculation_mode = data.get('calculation_mode', 'calculation_only')
        
        # Propofol
        c.propofol_concentration = data.get('propofol_concentration')
        c.target_dose = float(data.get('target_dose', 0))
        c.diluent_volume = float(data.get('diluent_volume', 0)) if data.get('diluent_volume') else None
        c.final_mixture_volume = float(data.get('final_mixture_volume', 0)) if data.get('final_mixture_volume') else None
        c.final_concentration = float(data.get('final_concentration', 0)) if data.get('final_concentration') else None
        c.total_propofol_mg = float(data.get('total_propofol_mg', 0)) if data.get('total_propofol_mg') else None
        
        # Bomba
        c.flow_ml_h = float(data.get('flow_ml_h', 0)) if data.get('flow_ml_h') else None
        c.vtbi_ml = float(data.get('vtbi_ml', 0)) if data.get('vtbi_ml') else None
        c.line_primed = data.get('line_primed')
        c.prime_fluid = data.get('prime_fluid')
        c.dead_volume_ml = float(data.get('dead_volume_ml', 0)) if data.get('dead_volume_ml') else None
        c.delay_time_min = float(data.get('delay_time_min', 0)) if data.get('delay_time_min') else None
        
        # Fisiológicos
        c.fc = int(data.get('fc')) if data.get('fc') else None
        c.fr = int(data.get('fr')) if data.get('fr') else None
        c.spo2 = int(data.get('spo2')) if data.get('spo2') else None
        c.pas = int(data.get('pas')) if data.get('pas') else None
        c.pam = int(data.get('pam')) if data.get('pam') else None
        c.temp = float(data.get('temp')) if data.get('temp') else None
        c.etco2 = int(data.get('etco2')) if data.get('etco2') else None
        
        # Transquirúrgico Real
        c.actual_volume_infused = float(data.get('actual_volume_infused', 0)) if data.get('actual_volume_infused') else None
        c.actual_propofol_mg = float(data.get('actual_propofol_mg', 0)) if data.get('actual_propofol_mg') else None
        c.actual_mg_kg = float(data.get('actual_mg_kg', 0)) if data.get('actual_mg_kg') else None
        c.actual_avg_dose_rate = float(data.get('actual_avg_dose_rate', 0)) if data.get('actual_avg_dose_rate') else None
        c.notes = data.get('notes')
        
        db.session.flush() # Obtener ID del caso
        
        # Guardar refuerzos de Ketamina
        for k in data.get('ketamine_events', []):
            ke = KetamineEvent(
                case_id=c.id,
                time_registered=k.get('time_registered', ''),
                dose_mg_kg=float(k.get('dose_mg_kg', 0)),
                volume_ml=float(k.get('volume_ml', 0)),
                reason=k.get('reason', '')
            )
            db.session.add(ke)
            
        # Guardar Lidocaína local
        l_data = data.get('lidocaine_event')
        if l_data:
            le = LidocaineEvent(
                case_id=c.id,
                linea_alba_ml=float(l_data.get('linea_alba_ml', 0)),
                ligamento_ml=float(l_data.get('ligamento_ml', 0)),
                peritoneal_ml=float(l_data.get('peritoneal_ml', 0)),
                piel_ml=float(l_data.get('piel_ml', 0)),
                total_mg=float(l_data.get('total_mg', 0)),
                percentage_of_max=float(l_data.get('percentage_of_max', 0))
            )
            db.session.add(le)
            
        db.session.commit()
        write_audit(current_user.id, 'case_saved', {'id': c.id, 'patient': c.patient_name})
        return jsonify({'success': True, 'id': c.id, 'message': 'Caso clínico guardado exitosamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error guardando caso: {str(e)}'}), 500

@app.route('/api/cases/<int:case_id>', methods=['GET'])
@login_required
def get_single_case(case_id):
    """Obtiene todos los detalles de un caso específico para duplicar o auditar."""
    c = AnesthesiaCase.query.get(case_id)
    if not c:
        return jsonify({'error': 'Caso no encontrado.'}), 404
        
    ke = [{
        'time_registered': k.time_registered,
        'dose_mg_kg': k.dose_mg_kg,
        'volume_ml': k.volume_ml,
        'reason': k.reason
    } for k in c.ketamine_events]
    
    le = {}
    if c.lidocaine_event:
        le = {
            'linea_alba_ml': c.lidocaine_event.linea_alba_ml,
            'ligamento_ml': c.lidocaine_event.ligamento_ml,
            'peritoneal_ml': c.lidocaine_event.peritoneal_ml,
            'piel_ml': c.lidocaine_event.piel_ml,
            'total_mg': c.lidocaine_event.total_mg,
            'percentage_of_max': c.lidocaine_event.percentage_of_max
        }
        
    return jsonify({
        'id': c.id,
        'date': c.date,
        'patient_name': c.patient_name,
        'species': c.species,
        'breed': c.breed,
        'weight': c.weight,
        'age': c.age,
        'asa_class': c.asa_class,
        'surgery_type': c.surgery_type,
        'duration_estimated': c.duration_estimated,
        'duration_real': c.duration_real,
        'calculation_mode': c.calculation_mode,
        'propofol_concentration': c.propofol_concentration,
        'target_dose': c.target_dose,
        'diluent_volume': c.diluent_volume,
        'final_mixture_volume': c.final_mixture_volume,
        'final_concentration': c.final_concentration,
        'total_propofol_mg': c.total_propofol_mg,
        'flow_ml_h': c.flow_ml_h,
        'vtbi_ml': c.vtbi_ml,
        'line_primed': c.line_primed,
        'prime_fluid': c.prime_fluid,
        'dead_volume_ml': c.dead_volume_ml,
        'delay_time_min': c.delay_time_min,
        'fc': c.fc,
        'fr': c.fr,
        'spo2': c.spo2,
        'pas': c.pas,
        'pam': c.pam,
        'temp': c.temp,
        'etco2': c.etco2,
        'actual_volume_infused': c.actual_volume_infused,
        'actual_propofol_mg': c.actual_propofol_mg,
        'actual_mg_kg': c.actual_mg_kg,
        'actual_avg_dose_rate': c.actual_avg_dose_rate,
        'notes': c.notes,
        'ketamine_events': ke,
        'lidocaine_event': le
    })

@app.route('/api/cases/<int:case_id>/delete', methods=['POST'])
@login_required
def delete_case(case_id):
    c = AnesthesiaCase.query.get(case_id)
    if not c:
        return jsonify({'success': False, 'message': 'Caso no encontrado.'}), 404
    try:
        pname = c.patient_name
        db.session.delete(c)
        db.session.commit()
        write_audit(current_user.id, 'case_deleted', {'id': case_id, 'patient': pname})
        return jsonify({'success': True, 'message': 'Caso clínico eliminado exitosamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al eliminar: {str(e)}'}), 500

@app.route('/api/cases/<int:case_id>/export', methods=['GET'])
@login_required
def export_partenvet(case_id):
    """Genera el JSON consolidado exacto estructurado para futuras sincronizaciones en PartenVet."""
    c = AnesthesiaCase.query.get(case_id)
    if not c:
        return jsonify({'error': 'Caso no encontrado.'}), 404
        
    c.exported = True
    db.session.commit()
    
    ke = [{
        'time': k.time_registered,
        'dose_mg_kg': k.dose_mg_kg,
        'volume_ml': k.volume_ml,
        'reason': k.reason
    } for k in c.ketamine_events]
    
    le = {}
    if c.lidocaine_event:
        le = {
            'linea_alba_ml': c.lidocaine_event.linea_alba_ml,
            'ligamento_ml': c.lidocaine_event.ligamento_ml,
            'peritoneal_ml': c.lidocaine_event.peritoneal_ml,
            'piel_ml': c.lidocaine_event.piel_ml,
            'total_mg': c.lidocaine_event.total_mg,
            'pct_of_max_safe': c.lidocaine_event.percentage_of_max
        }
        
    export_payload = {
        "export_version": "1.0",
        "exported_at": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "case_data": {
            "id": c.id,
            "date": c.date,
            "patient": {
                "name": c.patient_name,
                "species": c.species,
                "breed": c.breed,
                "weight_kg": c.weight,
                "age": c.age,
                "asa": c.asa_class
            },
            "procedure": {
                "type": c.surgery_type,
                "duration_estimated_min": c.duration_estimated,
                "duration_real_min": c.duration_real
            },
            "propofol_infusion": {
                "concentration": c.propofol_concentration,
                "target_dose_mg_kg_min": c.target_dose,
                "diluent_volume_ml": c.diluent_volume,
                "final_mixture_volume_ml": c.final_mixture_volume,
                "final_concentration_mg_ml": c.final_concentration,
                "flow_ml_h": c.flow_ml_h,
                "vtbi_ml": c.vtbi_ml
            },
            "physiological_monitoring": {
                "fc": c.fc,
                "fr": c.fr,
                "spo2": c.spo2,
                "pas": c.pas,
                "pam": c.pam,
                "temp": c.temp,
                "etco2": c.etco2
            },
            "intraoperative_events": {
                "ketamine_reinforcements": ke,
                "lidocaine_local": le
            },
            "outcome": {
                "total_volume_infused_real_ml": c.actual_volume_infused,
                "total_propofol_infused_real_mg": c.actual_propofol_mg,
                "real_avg_dose_rate_mg_kg_min": c.actual_avg_dose_rate
            }
        }
    }
    
    write_audit(current_user.id, 'case_exported_partenvet', {'id': c.id})
    return jsonify(export_payload)

# ==========================================
# BITÁCORA DE AUDITORÍA Y RESPALDOS
# ==========================================

@app.route('/api/audit-logs', methods=['GET'])
@login_required
def get_audit_logs():
    logs = AuditLog.query.order_by(AuditLog.id.desc()).limit(100).all()
    out = []
    for l in logs:
        out.append({
            'id': l.id,
            'timestamp': l.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': l.user_id,
            'action': l.action,
            'details': l.details,
            'ip_address': l.ip_address
        })
    return jsonify(out)

@app.route('/api/backup/export', methods=['GET'])
@login_required
def export_backup_json():
    """Genera un archivo JSON de respaldo de todos los casos del historial."""
    cases = AnesthesiaCase.query.all()
    backup_data = []
    
    for c in cases:
        ke = [{
            'time_registered': k.time_registered,
            'dose_mg_kg': k.dose_mg_kg,
            'volume_ml': k.volume_ml,
            'reason': k.reason
        } for k in c.ketamine_events]
        
        le = {}
        if c.lidocaine_event:
            le = {
                'linea_alba_ml': c.lidocaine_event.linea_alba_ml,
                'ligamento_ml': c.lidocaine_event.ligamento_ml,
                'peritoneal_ml': c.lidocaine_event.peritoneal_ml,
                'piel_ml': c.lidocaine_event.piel_ml,
                'total_mg': c.lidocaine_event.total_mg,
                'percentage_of_max': c.lidocaine_event.percentage_of_max
            }
            
        backup_data.append({
            'date': c.date,
            'patient_name': c.patient_name,
            'species': c.species,
            'breed': c.breed,
            'weight': c.weight,
            'age': c.age,
            'asa_class': c.asa_class,
            'surgery_type': c.surgery_type,
            'duration_estimated': c.duration_estimated,
            'duration_real': c.duration_real,
            'calculation_mode': c.calculation_mode,
            'propofol_concentration': c.propofol_concentration,
            'target_dose': c.target_dose,
            'diluent_volume': c.diluent_volume,
            'final_mixture_volume': c.final_mixture_volume,
            'final_concentration': c.final_concentration,
            'total_propofol_mg': c.total_propofol_mg,
            'flow_ml_h': c.flow_ml_h,
            'vtbi_ml': c.vtbi_ml,
            'line_primed': c.line_primed,
            'prime_fluid': c.prime_fluid,
            'dead_volume_ml': c.dead_volume_ml,
            'delay_time_min': c.delay_time_min,
            'fc': c.fc,
            'fr': c.fr,
            'spo2': c.spo2,
            'pas': c.pas,
            'pam': c.pam,
            'temp': c.temp,
            'etco2': c.etco2,
            'actual_volume_infused': c.actual_volume_infused,
            'actual_propofol_mg': c.actual_propofol_mg,
            'actual_mg_kg': c.actual_mg_kg,
            'actual_avg_dose_rate': c.actual_avg_dose_rate,
            'notes': c.notes,
            'ketamine_events': ke,
            'lidocaine_event': le
        })
        
    write_audit(current_user.id, 'backup_exported_json', {'total_cases': len(backup_data)})
    
    # Crear archivo de texto JSON descargable
    filename = f"safeanesthesia_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    temp_path = os.path.join(app.root_path, filename)
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
    @app.after_request
    def remove_file(response):
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as error:
            app.logger.error("Error al remover archivo temporal de backup", error)
        return response
        
    return send_file(temp_path, as_attachment=True, download_name=filename)

@app.route('/api/backup/import', methods=['POST'])
@login_required
def import_backup_json():
    """Restaura o añade cirugías a la base de datos a partir de un JSON de respaldo."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No se encontró archivo en la petición.'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Nombre de archivo vacío.'}), 400
        
    try:
        data = json.load(file)
        imported_count = 0
        
        for item in data:
            c = AnesthesiaCase()
            db.session.add(c)
            
            c.date = item.get('date')
            c.patient_name = item.get('patient_name')
            c.species = item.get('species')
            c.breed = item.get('breed')
            c.weight = float(item.get('weight', 0))
            c.age = item.get('age')
            c.asa_class = item.get('asa_class')
            c.surgery_type = item.get('surgery_type')
            c.duration_estimated = float(item.get('duration_estimated', 0))
            c.duration_real = float(item.get('duration_real', 0)) if item.get('duration_real') is not None else None
            c.calculation_mode = item.get('calculation_mode', 'calculation_only')
            c.propofol_concentration = item.get('propofol_concentration')
            c.target_dose = float(item.get('target_dose', 0))
            c.diluent_volume = float(item.get('diluent_volume', 0)) if item.get('diluent_volume') is not None else None
            c.final_mixture_volume = float(item.get('final_mixture_volume', 0)) if item.get('final_mixture_volume') is not None else None
            c.final_concentration = float(item.get('final_concentration', 0)) if item.get('final_concentration') is not None else None
            c.total_propofol_mg = float(item.get('total_propofol_mg', 0)) if item.get('total_propofol_mg') is not None else None
            c.flow_ml_h = float(item.get('flow_ml_h', 0)) if item.get('flow_ml_h') is not None else None
            c.vtbi_ml = float(item.get('vtbi_ml', 0)) if item.get('vtbi_ml') is not None else None
            c.line_primed = item.get('line_primed')
            c.prime_fluid = item.get('prime_fluid')
            c.dead_volume_ml = float(item.get('dead_volume_ml', 0)) if item.get('dead_volume_ml') is not None else None
            c.delay_time_min = float(item.get('delay_time_min', 0)) if item.get('delay_time_min') is not None else None
            
            c.fc = int(item.get('fc')) if item.get('fc') is not None else None
            c.fr = int(item.get('fr')) if item.get('fr') is not None else None
            c.spo2 = int(item.get('spo2')) if item.get('spo2') is not None else None
            c.pas = int(item.get('pas')) if item.get('pas') is not None else None
            c.pam = int(item.get('pam')) if item.get('pam') is not None else None
            c.temp = float(item.get('temp')) if item.get('temp') is not None else None
            c.etco2 = int(item.get('etco2')) if item.get('etco2') is not None else None
            
            c.actual_volume_infused = float(item.get('actual_volume_infused', 0)) if item.get('actual_volume_infused') is not None else None
            c.actual_propofol_mg = float(item.get('actual_propofol_mg', 0)) if item.get('actual_propofol_mg') is not None else None
            c.actual_mg_kg = float(item.get('actual_mg_kg', 0)) if item.get('actual_mg_kg') is not None else None
            c.actual_avg_dose_rate = float(item.get('actual_avg_dose_rate', 0)) if item.get('actual_avg_dose_rate') is not None else None
            c.notes = item.get('notes')
            
            db.session.flush()
            
            # Guardar eventos de ketamina
            for k in item.get('ketamine_events', []):
                ke = KetamineEvent(
                    case_id=c.id,
                    time_registered=k.get('time_registered'),
                    dose_mg_kg=float(k.get('dose_mg_kg', 0)),
                    volume_ml=float(k.get('volume_ml', 0)),
                    reason=k.get('reason')
                )
                db.session.add(ke)
                
            # Guardar eventos de lidocaína
            le_data = item.get('lidocaine_event')
            if le_data:
                le = LidocaineEvent(
                    case_id=c.id,
                    linea_alba_ml=float(le_data.get('linea_alba_ml', 0)),
                    ligamento_ml=float(le_data.get('ligamento_ml', 0)),
                    peritoneal_ml=float(le_data.get('peritoneal_ml', 0)),
                    piel_ml=float(le_data.get('piel_ml', 0)),
                    total_mg=float(le_data.get('total_mg', 0)),
                    percentage_of_max=float(le_data.get('percentage_of_max', 0))
                )
                db.session.add(le)
                
            imported_count += 1
            
        db.session.commit()
        write_audit(current_user.id, 'backup_imported_json', {'total_imported': imported_count})
        return jsonify({'success': True, 'message': f'Se importaron {imported_count} registros al historial con éxito.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error en formato de importación: {str(e)}'}), 400

@app.route('/api/backup/db', methods=['GET'])
@login_required
def download_sqlite_db():
    """Descarga binaria directa del archivo database.db."""
    db_path = os.path.join(app.root_path, 'instance', 'database.db')
    if not os.path.exists(db_path):
        # En algunas versiones SQLite de SQLAlchemy la ruta es directa
        db_path = os.path.join(app.root_path, 'database.db')
        
    if os.path.exists(db_path):
        write_audit(current_user.id, 'backup_sqlite_downloaded', {})
        return send_file(db_path, as_attachment=True, download_name='safeanesthesia_database.db')
    return jsonify({'success': False, 'message': 'No se encontró el archivo de base de datos físico.'}), 404

# ==========================================
# MODO DESARROLLO (POPULATE)
# ==========================================

@app.route('/api/dev/populate', methods=['POST'])
@login_required
def populate_dev_data():
    """Pobla la base de datos con 10 cirugías simuladas en modo de desarrollo."""
    if not app.debug:
        return jsonify({'success': False, 'message': 'Acción disponible únicamente en Modo Desarrollo (DEBUG=True).'}), 403
        
    try:
        # Limpiar base de datos vieja
        AnesthesiaCase.query.delete()
        KetamineEvent.query.delete()
        LidocaineEvent.query.delete()
        
        # 10 Pacientes simulados
        mock_cases = [
            # Caso 1: OVH perra
            {
                "patient_name": "Kira", "species": "dog", "breed": "Golden Retriever", "weight": 25.4, "age": "3 años",
                "asa_class": "I", "surgery_type": "ovh", "duration_estimated": 45, "duration_real": 50, "calculation_mode": "infusomat",
                "propofol_concentration": "1%", "target_dose": 0.25, "diluent_volume": 100, "final_mixture_volume": 128.57,
                "final_concentration": 2.22, "total_propofol_mg": 285.75, "flow_ml_h": 154.29, "vtbi_ml": 113.57,
                "line_primed": "yes", "prime_fluid": "mezcla", "dead_volume_ml": 15.0, "delay_time_min": 0.0,
                "fc": 95, "fr": 14, "spo2": 99, "pas": 110, "pam": 82, "temp": 37.8, "etco2": 38,
                "actual_volume_infused": 110.0, "actual_propofol_mg": 244.2, "actual_mg_kg": 9.61, "actual_avg_dose_rate": 0.19,
                "notes": "Procedimiento OVH standard. Tracción del pedículo izquierdo causó leve taquicardia transitoria, se aplicó un bolo de ketamina.",
                "ketamine_events": [{"time_registered": "10:15", "dose_mg_kg": 0.5, "volume_ml": 0.25, "reason": "Tracción pedículo izquierdo"}],
                "lidocaine_event": {"linea_alba_ml": 2.0, "ligamento_ml": 2.0, "peritoneal_ml": 0.0, "piel_ml": 1.0, "total_mg": 100.0, "percentage_of_max": 49.2}
            },
            # Caso 2: Castración perro
            {
                "patient_name": "Toby", "species": "dog", "breed": "Pug", "weight": 8.2, "age": "5 años",
                "asa_class": "II", "surgery_type": "castration", "duration_estimated": 30, "duration_real": 25, "calculation_mode": "calculation_only",
                "propofol_concentration": "1%", "target_dose": 0.2, "diluent_volume": 0.0, "final_mixture_volume": 6.15,
                "final_concentration": 10.0, "total_propofol_mg": 61.5, "flow_ml_h": 0.0, "vtbi_ml": 0.0,
                "line_primed": "no", "prime_fluid": "suero", "dead_volume_ml": 0.0, "delay_time_min": 0.0,
                "fc": 110, "fr": 18, "spo2": 98, "pas": 105, "pam": 78, "temp": 38.1, "etco2": 41,
                "actual_volume_infused": 5.0, "actual_propofol_mg": 50.0, "actual_mg_kg": 6.1, "actual_avg_dose_rate": 0.24,
                "notes": "Castración sin complicaciones. Recuperación rápida.",
                "ketamine_events": [],
                "lidocaine_event": {"linea_alba_ml": 0.5, "ligamento_ml": 1.0, "peritoneal_ml": 0.0, "piel_ml": 0.5, "total_mg": 40.0, "percentage_of_max": 61.0}
            },
            # Caso 3: Gato OVH prolongada (>60 min)
            {
                "patient_name": "Luna", "species": "cat", "breed": "Siames", "weight": 3.2, "age": "2 años",
                "asa_class": "II", "surgery_type": "ovh", "duration_estimated": 70, "duration_real": 65, "calculation_mode": "infusomat",
                "propofol_concentration": "1%", "target_dose": 0.2, "diluent_volume": 40, "final_mixture_volume": 44.48,
                "final_concentration": 1.01, "total_propofol_mg": 44.8, "flow_ml_h": 38.13, "vtbi_ml": 44.48,
                "line_primed": "yes", "prime_fluid": "suero", "dead_volume_ml": 15.0, "delay_time_min": 23.6,
                "fc": 140, "fr": 22, "spo2": 97, "pas": 90, "pam": 65, "temp": 36.9, "etco2": 44,
                "actual_volume_infused": 40.0, "actual_propofol_mg": 40.4, "actual_mg_kg": 12.6, "actual_avg_dose_rate": 0.19,
                "notes": "Alerta por duración en felino activa. Recuperación levemente lenta pero sin delirios ni cuerpos de Heinz evidentes.",
                "ketamine_events": [],
                "lidocaine_event": {"linea_alba_ml": 0.2, "ligamento_ml": 0.2, "peritoneal_ml": 0.0, "piel_ml": 0.2, "total_mg": 12.0, "percentage_of_max": 93.8}
            }
        ]
        
        # Poblar con datos simulados extra para llegar a 10 casos
        from random import choice, randint, uniform
        names = ["Thor", "Simba", "Rocky", "Max", "Lola", "Mia", "Bella"]
        breeds_dog = ["Mestizo", "Poodle", "Labrador", "Chihuahua"]
        breeds_cat = ["Persa", "Común Europeo", "Angora"]
        surgeries = ["laparotomy", "mastectomy", "cesarean"]
        
        for i in range(7):
            spec = choice(["dog", "cat"])
            br = choice(breeds_dog) if spec == "dog" else choice(breeds_cat)
            w = round(uniform(4.0, 30.0), 1) if spec == "dog" else round(uniform(2.5, 5.5), 1)
            asa = choice(["I", "II", "III", "IV"])
            surg = choice(surgeries)
            dur = randint(30, 90)
            
            mock_cases.append({
                "patient_name": names[i], "species": spec, "breed": br, "weight": w, "age": f"{randint(1,10)} años",
                "asa_class": asa, "surgery_type": surg, "duration_estimated": dur, "duration_real": dur + randint(-5, 10),
                "calculation_mode": choice(["calculation_only", "infusomat"]), "propofol_concentration": choice(["1%", "2%"]),
                "target_dose": round(uniform(0.12, 0.35), 2), "diluent_volume": choice([40, 50, 100]),
                "final_mixture_volume": w * 1.5, "final_concentration": 2.5, "total_propofol_mg": w * 15,
                "flow_ml_h": round(uniform(15.0, 80.0), 1), "vtbi_ml": w * 1.2,
                "line_primed": choice(["yes", "no"]), "prime_fluid": choice(["suero", "mezcla"]), "dead_volume_ml": 15.0, "delay_time_min": 0.0,
                "fc": randint(85, 160), "fr": randint(12, 26), "spo2": randint(96, 100), "pas": randint(90, 130), "pam": randint(60, 95),
                "temp": round(uniform(36.5, 38.8), 1), "etco2": randint(35, 45),
                "actual_volume_infused": w * 1.1, "actual_propofol_mg": w * 11, "actual_mg_kg": round(uniform(5.0, 12.0), 1),
                "actual_avg_dose_rate": round(uniform(0.1, 0.3), 2),
                "notes": f"Caso simulado de testeo clínico para cirugía de {surg}.",
                "ketamine_events": [],
                "lidocaine_event": {"linea_alba_ml": 0.5, "ligamento_ml": 0.0, "peritoneal_ml": 0.5, "piel_ml": 0.5, "total_mg": 30.0, "percentage_of_max": 40.0}
            })
            
        for idx, mc in enumerate(mock_cases):
            c = AnesthesiaCase()
            db.session.add(c)
            
            c.date = (datetime.utcnow().strftime('%Y-%m-%d'))
            c.patient_name = mc["patient_name"]
            c.species = mc["species"]
            c.breed = mc["breed"]
            c.weight = mc["weight"]
            c.age = mc["age"]
            c.asa_class = mc["asa_class"]
            c.surgery_type = mc["surgery_type"]
            c.duration_estimated = mc["duration_estimated"]
            c.duration_real = mc["duration_real"]
            c.calculation_mode = mc["calculation_mode"]
            c.propofol_concentration = mc["propofol_concentration"]
            c.target_dose = mc["target_dose"]
            c.diluent_volume = mc["diluent_volume"]
            c.final_mixture_volume = mc["final_mixture_volume"]
            c.final_concentration = mc["final_concentration"]
            c.total_propofol_mg = mc["total_propofol_mg"]
            c.flow_ml_h = mc["flow_ml_h"]
            c.vtbi_ml = mc["vtbi_ml"]
            c.line_primed = mc["line_primed"]
            c.prime_fluid = mc["prime_fluid"]
            c.dead_volume_ml = mc["dead_volume_ml"]
            c.delay_time_min = mc["delay_time_min"]
            
            c.fc = mc["fc"]
            c.fr = mc["fr"]
            c.spo2 = mc["spo2"]
            c.pas = mc["pas"]
            c.pam = mc["pam"]
            c.temp = mc["temp"]
            c.etco2 = mc["etco2"]
            
            c.actual_volume_infused = mc["actual_volume_infused"]
            c.actual_propofol_mg = mc["actual_propofol_mg"]
            c.actual_mg_kg = mc["actual_mg_kg"]
            c.actual_avg_dose_rate = mc["actual_avg_dose_rate"]
            c.notes = mc["notes"]
            
            db.session.flush()
            
            # Guardar eventos
            for k in mc["ketamine_events"]:
                ke = KetamineEvent(
                    case_id=c.id,
                    time_registered=k["time_registered"],
                    dose_mg_kg=k["dose_mg_kg"],
                    volume_ml=k["volume_ml"],
                    reason=k["reason"]
                )
                db.session.add(ke)
                
            le_data = mc["lidocaine_event"]
            le = LidocaineEvent(
                case_id=c.id,
                linea_alba_ml=le_data["linea_alba_ml"],
                ligamento_ml=le_data["ligamento_ml"],
                peritoneal_ml=le_data["peritoneal_ml"],
                piel_ml=le_data["piel_ml"],
                total_mg=le_data["total_mg"],
                percentage_of_max=le_data["percentage_of_max"]
            )
            db.session.add(le)
            
        db.session.commit()
        write_audit(current_user.id, 'dev_populated', {'cases_count': len(mock_cases)})
        return jsonify({'success': True, 'message': f'Base de datos poblada con éxito con {len(mock_cases)} procedimientos ficticios de prueba.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error en poblamiento: {str(e)}'}), 500

# ==========================================
# INICIALIZACIÓN
# ==========================================

with app.app_context():
    # Creación de tablas
    db.create_all()
    
    # Crear usuario Administrador inicial si no hay usuarios en la base de datos
    if not User.query.filter_by(username='Administrador').first():
        hashed_password = bcrypt.generate_password_hash('PartenVet2026!').decode('utf-8')
        admin = User(username='Administrador', password_hash=hashed_password)
        db.session.add(admin)
        db.session.commit()
        
        # Loguear evento
        log = AuditLog(
            action='system_initialization',
            details='Administrador creado con contraseña predeterminada.',
            ip_address='127.0.0.1'
        )
        db.session.add(log)
        db.session.commit()
        print("=> Base de datos inicializada. Contraseña inicial: PartenVet2026!")

if __name__ == '__main__':
    app.run(debug=True)
