from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


# ─── Usuario ──────────────────────────────────────────────────────────────────
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)
    cases      = db.relationship('AnesthesiaCase', backref='author', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


# ─── Caso Anestésico ───────────────────────────────────────────────────────────
class AnesthesiaCase(db.Model):
    __tablename__ = 'anesthesia_cases'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Datos del paciente
    patient_name = db.Column(db.String(100), nullable=False)
    species      = db.Column(db.String(20),  nullable=False)   # 'dog' | 'cat'
    weight_kg    = db.Column(db.Float,       nullable=False)
    age          = db.Column(db.String(30),  nullable=True)
    asa          = db.Column(db.String(5),   nullable=False)   # I…V
    surgery_type = db.Column(db.String(200), nullable=False)

    # Parámetros de infusión planificados
    duration_min_estimated = db.Column(db.Integer,  nullable=False)
    propofol_pct           = db.Column(db.Float,    nullable=False)   # 1.0 | 2.0
    target_dose_mg_kg_min  = db.Column(db.Float,    nullable=False)
    diluent_volume_ml      = db.Column(db.Float,    nullable=False)
    dead_volume_ml         = db.Column(db.Float,    nullable=True)
    flow_ml_h              = db.Column(db.Float,    nullable=True)
    vtbi_ml                = db.Column(db.Float,    nullable=True)
    final_conc_mg_ml       = db.Column(db.Float,    nullable=True)
    total_propofol_mg      = db.Column(db.Float,    nullable=True)

    # Resultados reales (post-operatorios)
    duration_min_real      = db.Column(db.Integer,  nullable=True)
    volume_infused_real_ml = db.Column(db.Float,    nullable=True)
    propofol_infused_real_mg = db.Column(db.Float,  nullable=True)
    real_avg_dose_mg_kg_min  = db.Column(db.Float,  nullable=True)

    # Exportación
    exported    = db.Column(db.Boolean, default=False)
    exported_at = db.Column(db.DateTime, nullable=True)

    events = db.relationship('CaseEvent', backref='case', lazy=True,
                             cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AnesthesiaCase id={self.id} patient={self.patient_name}>'


# ─── Evento Intraoperatorio ────────────────────────────────────────────────────
class CaseEvent(db.Model):
    __tablename__ = 'case_events'

    id         = db.Column(db.Integer, primary_key=True)
    case_id    = db.Column(db.Integer, db.ForeignKey('anesthesia_cases.id'), nullable=False)
    event_type = db.Column(db.String(50),  nullable=False)  # 'ketamine_bolus' | 'lidocaine_block'
    timestamp  = db.Column(db.DateTime,    default=datetime.utcnow)
    details    = db.Column(db.Text,        nullable=True)   # JSON serializado

    def __repr__(self):
        return f'<CaseEvent {self.event_type} case={self.case_id}>'


# ─── Bitácora de Auditoría ─────────────────────────────────────────────────────
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id         = db.Column(db.Integer, primary_key=True)
    timestamp  = db.Column(db.DateTime, default=datetime.utcnow)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action     = db.Column(db.String(100), nullable=False)
    # 'login' | 'logout' | 'calculation_generated' | 'case_saved' |
    # 'case_edited' | 'pdf_generated' | 'case_exported'
    details    = db.Column(db.Text,        nullable=True)  # JSON serializado
    ip_address = db.Column(db.String(45),  nullable=True)

    def __repr__(self):
        return f'<AuditLog {self.action} user={self.user_id}>'
