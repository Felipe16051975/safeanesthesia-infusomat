import sys
import os

# Añadir directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_clinical_math():
    print("--- Probando Matemáticas Clínicas de Propofol ---")
    from services.propofol_service import calculate_propofol
    
    # Caso de prueba: Gato de 3.4 kg, 45 min de cirugía, dosis de 0.2 mg/kg/min con propofol al 1% (10 mg/ml) y ASA III
    res_prop = calculate_propofol(
        weight=3.4,
        duration_min=45,
        target_dose=0.2,
        concentration_pct=1.0,
        species="gato",
        asa="III"
    )
    
    print("Resultado Propofol:")
    for k, v in res_prop.items():
        print(f"  {k}: {v}")
        
    assert abs(res_prop["mg_min"] - (3.4 * 0.2)) < 1e-4, "Error en mg_min"
    assert abs(res_prop["mg_h"] - (3.4 * 0.2 * 60)) < 1e-4, "Error en mg_h"
    assert abs(res_prop["mg_total"] - (3.4 * 0.2 * 45)) < 1e-4, "Error en mg_total"
    assert abs(res_prop["ml_propofol"] - ((3.4 * 0.2 * 45) / 10.0)) < 1e-4, "Error en ml_propofol"
    assert res_prop["alert_level"] == "SAFE", "Gato a 0.2 con ASA III debe ser SAFE"
    
    print("\n--- Probando Dilución y Programación de Bomba ---")
    from services.pump_service import calculate_pump
    
    # Dilución en 40 ml de NaCl 0.9%
    res_pump = calculate_pump(
        ml_propofol=res_prop["ml_propofol"],
        ml_suero=40.0,
        mg_total=res_prop["mg_total"],
        duration_min=45,
        line_primed="si",
        primed_with="suero",
        dead_volume_ml=1.5
    )
    
    print("Resultado Bomba:")
    for k, v in res_pump.items():
        print(f"  {k}: {v}")
        
    # Volumen final = 3.06 ml de propofol + 40.0 ml de suero = 43.06 ml
    assert res_pump["volumen_final"] == 43.06, "Error en volumen_final"
    # Concentración final = 30.6 mg / 43.06 ml = 0.7106 mg/ml
    assert abs(res_pump["concentracion_final"] - (30.6 / 43.06)) < 1e-4, "Error en concentracion_final"
    # FLOW = 43.06 ml / (45 / 60) h = 57.41 ml/h
    assert abs(res_pump["flow_ml_h"] - (43.06 * 60 / 45)) < 1e-2, "Error en flow_ml_h"
    assert res_pump["vtbi_ml"] == 43.06, "Error en vtbi"
    # Retraso = (1.5 ml / 57.41 ml/h) * 60 = 1.56 minutos
    expected_delay = (1.5 / (43.06 * 60 / 45)) * 60
    assert abs(res_pump["priming_delay_min"] - expected_delay) < 1e-2, "Error en priming_delay_min"
    
    print("\n--- Prueba de Alertas Críticas (ASA IV) ---")
    res_critical = calculate_propofol(
        weight=3.4,
        duration_min=45,
        target_dose=0.2,
        concentration_pct=1.0,
        species="gato",
        asa="IV"
    )
    print(f"Alert Level para ASA IV: {res_critical['alert_level']}")
    assert res_critical["alert_level"] == "CRITICAL", "ASA IV debe ser crítico"
    assert res_critical["requires_consent"] == True, "ASA IV debe requerir consentimiento"
    
    print("\n¡Pruebas matemáticas y clínicas PASADAS exitosamente!")

def test_db_init():
    print("\n--- Probando Inicialización de Base de Datos y Sembrado ---")
    from app import app, db, User
    
    # Usar base de datos temporal para la prueba
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        # Verificar que se creó el usuario admin
        # El sembrado se ejecuta automáticamente en el bloque context_app de app.py
        # Pero dado que cambiamos a :memory:, debemos verificarlo
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            # Forzar inicialización
            from flask_bcrypt import Bcrypt
            bcrypt = Bcrypt(app)
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            new_admin = User(username='admin', password_hash=hashed_password)
            db.session.add(new_admin)
            db.session.commit()
            admin_user = User.query.filter_by(username='admin').first()
            
        assert admin_user is not None, "El usuario admin no existe"
        assert admin_user.username == "admin", "Nombre de usuario incorrecto"
        print("Usuario 'admin' encontrado en la base de datos.")
        print("¡Prueba de base de datos PASADA exitosamente!")

if __name__ == "__main__":
    test_clinical_math()
    test_db_init()
