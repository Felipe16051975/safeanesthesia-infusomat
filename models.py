from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

class AnesthesiaCase(db.Model):
    __tablename__ = 'anesthesia_cases'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), default=lambda: datetime.utcnow().strftime('%Y-%m-%d'))
    patient_name = db.Column(db.String(100), nullable=False)
    species = db.Column(db.String(50), nullable=False) # 'dog' / 'cat'
    breed = db.Column(db.String(100))
    weight = db.Column(db.Float, nullable=False)
    age = db.Column(db.String(50))
    asa_class = db.Column(db.String(5), nullable=False) # 'I', 'II', 'III', 'IV', 'V'
    surgery_type = db.Column(db.String(100), nullable=False)
    duration_estimated = db.Column(db.Float, nullable=False)
    duration_real = db.Column(db.Float)
    calculation_mode = db.Column(db.String(20), nullable=False) # 'calculation_only' / 'infusomat'
    
    # Propofol
    propofol_concentration = db.Column(db.String(5), nullable=False) # '1%' / '2%'
    target_dose = db.Column(db.Float, nullable=False) # mg/kg/min
    diluent_volume = db.Column(db.Float) # ml
    final_mixture_volume = db.Column(db.Float) # ml
    final_concentration = db.Column(db.Float) # mg/ml
    total_propofol_mg = db.Column(db.Float) # mg
    
    # Bomba
    flow_ml_h = db.Column(db.Float) # ml/h
    vtbi_ml = db.Column(db.Float) # ml
    line_primed = db.Column(db.String(3)) # 'yes' / 'no'
    prime_fluid = db.Column(db.String(20)) # 'suero' / 'mezcla'
    dead_volume_ml = db.Column(db.Float) # ml
    delay_time_min = db.Column(db.Float) # minutos
    
    # Fisiológico / Monitorización
    fc = db.Column(db.Integer) # lpm
    fr = db.Column(db.Integer) # rpm
    spo2 = db.Column(db.Integer) # %
    pas = db.Column(db.Integer) # mmHg
    pam = db.Column(db.Integer) # mmHg
    temp = db.Column(db.Float) # °C
    etco2 = db.Column(db.Integer) # mmHg
    
    # Transquirúrgico Real
    actual_volume_infused = db.Column(db.Float) # ml
    actual_propofol_mg = db.Column(db.Float) # mg
    actual_mg_kg = db.Column(db.Float) # mg/kg
    actual_avg_dose_rate = db.Column(db.Float) # mg/kg/min
    notes = db.Column(db.Text)
    exported = db.Column(db.Boolean, default=False)

    # Relaciones
    ketamine_events = db.relationship('KetamineEvent', backref='case', lazy=True, cascade="all, delete-orphan")
    lidocaine_event = db.relationship('LidocaineEvent', backref='case', uselist=False, lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<AnesthesiaCase {self.id} - {self.patient_name}>'

class KetamineEvent(db.Model):
    __tablename__ = 'ketamine_events'
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('anesthesia_cases.id'), nullable=False)
    time_registered = db.Column(db.String(5), nullable=False) # '12:30'
    dose_mg_kg = db.Column(db.Float, nullable=False)
    volume_ml = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(255))

    def __repr__(self):
        return f'<KetamineEvent {self.id} (Case {self.case_id})>'

class LidocaineEvent(db.Model):
    __tablename__ = 'lidocaine_events'
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('anesthesia_cases.id'), nullable=False)
    linea_alba_ml = db.Column(db.Float, default=0.0)
    ligamento_ml = db.Column(db.Float, default=0.0)
    peritoneal_ml = db.Column(db.Float, default=0.0)
    piel_ml = db.Column(db.Float, default=0.0)
    total_mg = db.Column(db.Float, default=0.0)
    percentage_of_max = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f'<LidocaineEvent {self.id} (Case {self.case_id})>'

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, nullable=True)
    action = db.Column(db.String(100), nullable=False) # 'login', 'logout', etc.
    details = db.Column(db.Text) # JSON serializado o texto
    ip_address = db.Column(db.String(45))

    def __repr__(self):
        return f'<AuditLog {self.action} at {self.timestamp}>'
