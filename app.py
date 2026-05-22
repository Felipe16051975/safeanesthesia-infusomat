import os
import json
from datetime import datetime

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

# ─── Entorno ───────────────────────────────────────────────────────────────────
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY']                  = os.getenv('SECRET_KEY', 'safe_secret_key_1029384756')
app.config['SQLALCHEMY_DATABASE_URI']     = os.getenv('DATABASE_URL', 'sqlite:///safeanesthesia.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ─── Extensiones ───────────────────────────────────────────────────────────────
from models import db, User, AnesthesiaCase, CaseEvent, AuditLog
db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view         = 'login'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ─── Inicialización de DB ──────────────────────────────────────────────────────
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed = bcrypt.generate_password_hash('admin123').decode('utf-8')
        db.session.add(User(username='admin', password_hash=hashed))
        db.session.commit()
        print("Base de datos inicializada. Usuario 'admin' creado (contraseña: admin123).")


# ─── Helper de Auditoría ───────────────────────────────────────────────────────
def write_audit(action, details=None):
    """Registra una acción en la bitácora de auditoría."""
    try:
        log = AuditLog(
            user_id    = current_user.id if current_user.is_authenticated else None,
            action     = action,
            details    = json.dumps(details, ensure_ascii=False) if details else None,
            ip_address = request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass  # La auditoría nunca interrumpe el flujo clínico


# ══════════════════════════════════════════════════════════════════════════════
# RUTAS DE AUTENTICACIÓN
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            write_audit('login', {'username': username})
            return redirect(url_for('index'))
        else:
            write_audit('login_failed', {'username': username})
            flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    write_audit('logout')
    logout_user()
    flash('Sesión cerrada con éxito.', 'success')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    return render_template('index.html')


# ══════════════════════════════════════════════════════════════════════════════
# API — CÁLCULOS CLÍNICOS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/calculate', methods=['POST'])
@login_required
def api_calculate():
    """Propofol: dosis, dilución y programación Infusomat."""
    from services.propofol_service import calculate_propofol
    from services.pump_service import calculate_pump

    data = request.get_json() or {}
    try:
        weight            = float(data.get('weight', 0))
        duration_min      = int(data.get('durationMin', 0))
        target_dose       = float(data.get('targetDose', 0))
        concentration_pct = float(data.get('propofolConcentration', 1))
        species           = data.get('species', 'dog')
        asa               = data.get('asa', 'I')
        diluent_volume    = float(data.get('diluentVolume', 0))
        line_primed       = data.get('linePrimed', 'no')
        primed_with       = data.get('primedWith', 'suero')
        dead_volume       = float(data.get('deadVolume', 0))

        if weight <= 0 or duration_min <= 0 or target_dose <= 0:
            return jsonify({'success': False,
                            'error': 'El peso, la duración y la dosis objetivo deben ser mayores a cero.'}), 400

        prop_res = calculate_propofol(weight=weight, duration_min=duration_min,
                                      target_dose=target_dose,
                                      concentration_pct=concentration_pct,
                                      saline_ml=diluent_volume,
                                      species=species, asa=asa)

        pump_res = calculate_pump(volume_final=prop_res['volume_final'],
                                  flow_ml_h=prop_res['flow_ml_h'],
                                  vtbi_ml=prop_res['vtbi_ml'],
                                  time_min=prop_res['time_min'],
                                  dead_volume_ml=dead_volume,
                                  line_primed=line_primed,
                                  primed_with=primed_with)

        write_audit('calculation_generated', {
            'patient': data.get('patientName', ''), 'weight': weight,
            'species': species, 'asa': asa, 'target_dose': target_dose
        })

        return jsonify({'success': True, 'propofol': prop_res, 'pump': pump_res})

    except ValueError as ve:
        return jsonify({'success': False, 'error': f'Error de formato numérico: {ve}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Fallo interno: {e}'}), 500


@app.route('/api/calculate/ketamine', methods=['POST'])
@login_required
def api_calculate_ketamine():
    """Bolo de ketamina para refuerzo/profundización intraoperatoria."""
    from services.ketamine_service import calculate_ketamine

    data = request.get_json() or {}
    try:
        weight          = float(data.get('weight', 0))
        target_dose     = float(data.get('targetDose', 0.5))
        concentration   = float(data.get('concentrationMgMl', 50.0))

        if weight <= 0:
            return jsonify({'success': False, 'error': 'El peso debe ser mayor a cero.'}), 400

        result = calculate_ketamine(weight=weight, target_dose=target_dose,
                                    concentration_mg_ml=concentration)
        write_audit('ketamine_calculated', {'weight': weight, 'dose': target_dose})
        return jsonify({'success': True, 'ketamine': result})

    except ValueError as ve:
        return jsonify({'success': False, 'error': f'Error de formato: {ve}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Fallo interno: {e}'}), 500


@app.route('/api/calculate/lidocaine', methods=['POST'])
@login_required
def api_calculate_lidocaine():
    """Balance de toxicidad de lidocaína local por especie y anatomía."""
    from services.lidocaine_service import calculate_lidocaine

    data = request.get_json() or {}
    try:
        weight            = float(data.get('weight', 0))
        species           = data.get('species', 'dog')
        target_limit_dose = float(data.get('targetLimitDose', 10.0))
        concentration     = float(data.get('concentrationMgMl', 20.0))
        linea_alba_ml     = float(data.get('lineaAlbaMl', 0))
        ligamento_ml      = float(data.get('ligamentoMl', 0))
        peritoneal_ml     = float(data.get('peritonealMl', 0))
        piel_ml           = float(data.get('pielMl', 0))

        if weight <= 0:
            return jsonify({'success': False, 'error': 'El peso debe ser mayor a cero.'}), 400

        result = calculate_lidocaine(weight=weight, species=species,
                                     target_limit_dose=target_limit_dose,
                                     concentration_mg_ml=concentration,
                                     linea_alba_ml=linea_alba_ml,
                                     ligamento_ml=ligamento_ml,
                                     peritoneal_ml=peritoneal_ml,
                                     piel_ml=piel_ml)
        write_audit('lidocaine_calculated', {
            'weight': weight, 'species': species,
            'total_ml': linea_alba_ml + ligamento_ml + peritoneal_ml + piel_ml
        })
        return jsonify({'success': True, 'lidocaine': result})

    except ValueError as ve:
        return jsonify({'success': False, 'error': f'Error de formato: {ve}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Fallo interno: {e}'}), 500


@app.route('/api/config/limits', methods=['GET'])
@login_required
def api_config_limits():
    """Devuelve la configuración clínica JSON para validaciones en el cliente."""
    try:
        from services.propofol_service import load_limits
        return jsonify(load_limits())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# API — FASE 2: PROCEDIMIENTO, KETAMINA, LIDOCAÍNA
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/start-procedure', methods=['POST'])
@login_required
def api_start_procedure():
    """Inicia un procedimiento anestésico y devuelve un procedure_id."""
    from services.db import start_procedure
    data = request.get_json() or {}
    try:
        patient_name = data.get('patientName', 'Sin nombre')
        species      = data.get('species', 'dog')
        weight       = float(data.get('weight', 0))
        if weight <= 0:
            return jsonify({'success': False, 'error': 'El peso debe ser mayor a cero.'}), 400
        proc_id = start_procedure(patient_name=patient_name, species=species, weight=weight)
        write_audit('procedure_started', {'procedure_id': proc_id, 'patient': patient_name})
        return jsonify({'success': True, 'procedure_id': proc_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ketamine/meta', methods=['GET'])
@login_required
def api_ketamine_meta():
    """Devuelve meta-configuración de ketamina desde clinical_limits.json."""
    try:
        from services.ketamine_service import get_meta
        return jsonify({'success': True, 'meta': get_meta()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lidocaine/meta', methods=['GET'])
@login_required
def api_lidocaine_meta():
    """Devuelve meta-configuración de lidocaína desde clinical_limits.json."""
    try:
        from services.lidocaine_service import get_meta
        return jsonify({'success': True, 'meta': get_meta()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ketamine', methods=['POST'])
@login_required
def api_ketamine():
    """Calcula bolo de ketamina, lo registra como evento y devuelve resultado."""
    from services.ketamine_service import calculate_ketamine
    from services.db import add_event
    data = request.get_json() or {}
    try:
        weight              = float(data.get('weight', 0))
        target_dose         = float(data.get('targetDose', 0.5))
        concentration       = float(data.get('concentrationMgMl', 50.0))
        species             = data.get('species', 'dog')
        reason              = data.get('reason', None)
        accumulated_mg      = float(data.get('accumulatedMg', 0.0))
        procedure_id        = data.get('procedureId', None)

        if weight <= 0:
            return jsonify({'success': False, 'error': 'El peso debe ser mayor a cero.'}), 400

        result = calculate_ketamine(
            weight=weight,
            target_dose=target_dose,
            concentration_mg_ml=concentration,
            species=species,
            reason=reason,
            accumulated_mg=accumulated_mg,
        )

        if procedure_id is not None:
            add_event(int(procedure_id), 'ketamine_bolus', {
                'bolus_mg':            result['bolus_mg'],
                'bolus_ml':            result['bolus_ml'],
                'concentration_mg_ml': result['concentration_mg_ml'],
                'accumulated_mg':      result['accumulated_mg'],
                'new_accumulated_mg':  result['new_accumulated_mg'],
                'reinforcement_index': result['reinforcement_index'],
                'classification':      result['classification'],
                'reason':              reason,
            })

        write_audit('ketamine_bolus', {
            'weight': weight, 'dose': target_dose, 'species': species,
            'bolus_mg': result['bolus_mg'], 'procedure_id': procedure_id
        })
        return jsonify({'success': True, 'ketamine': result})

    except ValueError as ve:
        return jsonify({'success': False, 'error': f'Error de formato: {ve}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Fallo interno: {e}'}), 500


@app.route('/api/lidocaine', methods=['POST'])
@login_required
def api_lidocaine():
    """Calcula balance de lidocaína, registra evento y devuelve resultado."""
    from services.lidocaine_service import calculate_lidocaine
    from services.db import add_event
    data = request.get_json() or {}
    try:
        weight            = float(data.get('weight', 0))
        species           = data.get('species', 'dog')
        target_limit_dose = float(data.get('targetLimitDose', 8.0))
        concentration     = float(data.get('concentrationMgMl', 20.0))
        linea_alba_ml     = float(data.get('lineaAlbaMl', 0))
        ligamento_ml      = float(data.get('ligamentoMl', 0))
        peritoneal_ml     = float(data.get('peritonealMl', 0))
        piel_ml           = float(data.get('pielMl', 0))
        site              = data.get('site', None)
        procedure_id      = data.get('procedureId', None)

        if weight <= 0:
            return jsonify({'success': False, 'error': 'El peso debe ser mayor a cero.'}), 400

        result = calculate_lidocaine(
            weight=weight,
            species=species,
            target_limit_dose=target_limit_dose,
            concentration_mg_ml=concentration,
            linea_alba_ml=linea_alba_ml,
            ligamento_ml=ligamento_ml,
            peritoneal_ml=peritoneal_ml,
            piel_ml=piel_ml,
            site=site,
        )

        if procedure_id is not None:
            add_event(int(procedure_id), 'lidocaine_block', {
                'total_injected_mg': result['total_injected_mg'],
                'accumulated_mg':    result['accumulated_mg'],
                'remaining_mg':      result['remaining_mg'],
                'pct_of_max':        result['pct_of_max'],
                'status':            result['status'],
                'site':              site,
            })

        write_audit('lidocaine_block', {
            'weight': weight, 'species': species,
            'total_mg': result['total_injected_mg'], 'procedure_id': procedure_id
        })
        return jsonify({'success': True, 'lidocaine': result})

    except ValueError as ve:
        return jsonify({'success': False, 'error': f'Error de formato: {ve}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Fallo interno: {e}'}), 500


@app.route('/api/procedure/<int:procedure_id>/events', methods=['GET'])
@login_required
def api_procedure_events(procedure_id):
    """Devuelve el historial completo de eventos de un procedimiento."""
    from services.db import get_events
    try:
        events = get_events(procedure_id)
        return jsonify({'success': True, 'procedure_id': procedure_id, 'events': events})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# API — CASOS CLÍNICOS (CRUD)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/cases', methods=['POST'])
@login_required
def api_save_case():
    """Guarda un caso anestésico completo en la base de datos."""
    data = request.get_json() or {}
    try:
        case = AnesthesiaCase(
            user_id                = current_user.id,
            patient_name           = data.get('patientName', 'Sin nombre'),
            species                = data.get('species', 'dog'),
            weight_kg              = float(data.get('weight', 0)),
            age                    = data.get('age', ''),
            asa                    = data.get('asa', 'I'),
            surgery_type           = data.get('surgeryType', ''),
            duration_min_estimated = int(data.get('durationMin', 0)),
            propofol_pct           = float(data.get('propofolConcentration', 1.0)),
            target_dose_mg_kg_min  = float(data.get('targetDose', 0)),
            diluent_volume_ml      = float(data.get('diluentVolume', 0)),
            dead_volume_ml         = float(data.get('deadVolume', 0)),
            flow_ml_h              = float(data.get('flowMlH', 0)),
            vtbi_ml                = float(data.get('vtbiMl', 0)),
            final_conc_mg_ml       = float(data.get('finalConcMgMl', 0)),
            total_propofol_mg      = float(data.get('totalPropofolMg', 0)),
        )
        db.session.add(case)
        db.session.flush()  # obtener ID antes de commit

        # Guardar eventos intraoperatorios opcionales
        events = data.get('events', [])
        for ev in events:
            db.session.add(CaseEvent(
                case_id    = case.id,
                event_type = ev.get('type', 'generic'),
                details    = json.dumps(ev.get('details', {}), ensure_ascii=False)
            ))

        db.session.commit()
        write_audit('case_saved', {'case_id': case.id, 'patient': case.patient_name})
        return jsonify({'success': True, 'caseId': case.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cases/<int:case_id>', methods=['PUT'])
@login_required
def api_update_case(case_id):
    """Actualiza un caso con resultados post-operatorios reales."""
    case = db.session.get(AnesthesiaCase, case_id)
    if not case:
        return jsonify({'success': False, 'error': 'Caso no encontrado.'}), 404

    data = request.get_json() or {}
    try:
        if 'durationMinReal' in data:
            case.duration_min_real = int(data['durationMinReal'])
        if 'volumeInfusedRealMl' in data:
            case.volume_infused_real_ml = float(data['volumeInfusedRealMl'])
        if 'propofolInfusedRealMg' in data:
            case.propofol_infused_real_mg = float(data['propofolInfusedRealMg'])
        if 'realAvgDoseMgKgMin' in data:
            case.real_avg_dose_mg_kg_min = float(data['realAvgDoseMgKgMin'])
        case.updated_at = datetime.utcnow()

        db.session.commit()
        write_audit('case_edited', {'case_id': case.id})
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cases', methods=['GET'])
@login_required
def api_get_cases():
    """Devuelve los últimos casos y métricas del dashboard."""
    from sqlalchemy import func

    today = datetime.utcnow().date()

    cases_today   = AnesthesiaCase.query.filter(
        func.date(AnesthesiaCase.created_at) == today
    ).count()

    all_real      = AnesthesiaCase.query.filter(
        AnesthesiaCase.duration_min_real.isnot(None)
    ).all()
    avg_duration  = (
        round(sum(c.duration_min_real for c in all_real) / len(all_real), 1)
        if all_real else 0
    )

    ovh_count     = AnesthesiaCase.query.filter(
        AnesthesiaCase.surgery_type.ilike('%ovh%')
        | AnesthesiaCase.surgery_type.ilike('%ovario%')
        | AnesthesiaCase.surgery_type.ilike('%histerectom%')
    ).count()

    castr_count   = AnesthesiaCase.query.filter(
        AnesthesiaCase.surgery_type.ilike('%castrac%')
        | AnesthesiaCase.surgery_type.ilike('%orquiect%')
    ).count()

    last_10 = AnesthesiaCase.query.order_by(
        AnesthesiaCase.created_at.desc()
    ).limit(10).all()

    def serialize_case(c):
        return {
            'id':              c.id,
            'date':            c.created_at.strftime('%Y-%m-%d'),
            'patientName':     c.patient_name,
            'species':         c.species,
            'weight':          c.weight_kg,
            'asa':             c.asa,
            'surgeryType':     c.surgery_type,
            'durationEst':     c.duration_min_estimated,
            'durationReal':    c.duration_min_real,
            'flowMlH':         c.flow_ml_h,
            'vtbiMl':          c.vtbi_ml,
            'targetDose':      c.target_dose_mg_kg_min,
            'propofolConc':    c.propofol_pct,
            'diluentVolume':   c.diluent_volume_ml,
            'deadVolume':      c.dead_volume_ml,
            'realAvgDose':     c.real_avg_dose_mg_kg_min,
            'exported':        c.exported,
        }

    return jsonify({
        'success':     True,
        'stats': {
            'casesToday':    cases_today,
            'avgDuration':   avg_duration,
            'ovhCount':      ovh_count,
            'castrationCount': castr_count,
        },
        'recentCases': [serialize_case(c) for c in last_10]
    })


@app.route('/api/cases/<int:case_id>', methods=['GET'])
@login_required
def api_get_case(case_id):
    """Devuelve los datos de un caso individual."""
    case = db.session.get(AnesthesiaCase, case_id)
    if not case:
        return jsonify({'success': False, 'error': 'Caso no encontrado.'}), 404

    events = [{'type': e.event_type,
               'timestamp': e.timestamp.isoformat(),
               'details': json.loads(e.details) if e.details else {}}
              for e in case.events]

    return jsonify({'success': True, 'case': {
        'id':             case.id,
        'patientName':    case.patient_name,
        'species':        case.species,
        'weight':         case.weight_kg,
        'age':            case.age,
        'asa':            case.asa,
        'surgeryType':    case.surgery_type,
        'durationMin':    case.duration_min_estimated,
        'propofolConcentration': case.propofol_pct,
        'targetDose':     case.target_dose_mg_kg_min,
        'diluentVolume':  case.diluent_volume_ml,
        'deadVolume':     case.dead_volume_ml,
        'flowMlH':        case.flow_ml_h,
        'vtbiMl':         case.vtbi_ml,
        'finalConcMgMl':  case.final_conc_mg_ml,
        'totalPropofolMg': case.total_propofol_mg,
        'durationMinReal': case.duration_min_real,
        'volumeInfusedRealMl': case.volume_infused_real_ml,
        'propofolInfusedRealMg': case.propofol_infused_real_mg,
        'realAvgDoseMgKgMin': case.real_avg_dose_mg_kg_min,
        'exported':       case.exported,
        'events':         events,
    }})


# ══════════════════════════════════════════════════════════════════════════════
# API — EXPORTACIÓN PARTENVET (FASE 4)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/cases/<int:case_id>/export', methods=['GET'])
@login_required
def api_export_case(case_id):
    """Exporta un caso en el formato estructurado compatible con PartenVet."""
    case = db.session.get(AnesthesiaCase, case_id)
    if not case:
        return jsonify({'success': False, 'error': 'Caso no encontrado.'}), 404

    ketamine_events = []
    lidocaine_events = []
    for ev in case.events:
        detail = json.loads(ev.details) if ev.details else {}
        if ev.event_type == 'ketamine_bolus':
            ketamine_events.append({
                'time':        ev.timestamp.strftime('%H:%M'),
                'dose_mg_kg':  detail.get('dose_mg_kg'),
                'volume_ml':   detail.get('volume_ml'),
                'reason':      detail.get('reason', '')
            })
        elif ev.event_type == 'lidocaine_block':
            lidocaine_events.append(detail)

    lido_summary = lidocaine_events[-1] if lidocaine_events else {}

    payload = {
        'export_version': '1.0',
        'exported_at': datetime.utcnow().isoformat() + 'Z',
        'source': 'SafeAnesthesia Infusomat Propofol Module',
        'case_data': {
            'id': case.id,
            'date': case.created_at.strftime('%Y-%m-%d'),
            'patient': {
                'name':       case.patient_name,
                'species':    case.species,
                'weight_kg':  case.weight_kg,
                'age':        case.age,
                'asa':        case.asa,
            },
            'procedure': {
                'type':                  case.surgery_type,
                'duration_estimated_min': case.duration_min_estimated,
                'duration_real_min':     case.duration_min_real,
            },
            'propofol_infusion': {
                'concentration':              f'{int(case.propofol_pct)}%',
                'target_dose_mg_kg_min':      case.target_dose_mg_kg_min,
                'diluent_volume_ml':          case.diluent_volume_ml,
                'final_concentration_mg_ml':  case.final_conc_mg_ml,
                'flow_ml_h':                  case.flow_ml_h,
                'vtbi_ml':                    case.vtbi_ml,
            },
            'intraoperative_events': {
                'ketamine_reinforcements': ketamine_events,
                'lidocaine_local':         lido_summary,
            },
            'outcome': {
                'total_volume_infused_real_ml':  case.volume_infused_real_ml,
                'total_propofol_infused_real_mg': case.propofol_infused_real_mg,
                'real_avg_dose_rate_mg_kg_min':  case.real_avg_dose_mg_kg_min,
            }
        }
    }

    # Marcar como exportado
    case.exported    = True
    case.exported_at = datetime.utcnow()
    db.session.commit()
    write_audit('case_exported', {'case_id': case.id, 'patient': case.patient_name})

    return jsonify(payload)


if __name__ == '__main__':
    app.run(debug=True)
