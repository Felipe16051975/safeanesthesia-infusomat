import json
from services.propofol_service import calculate_propofol
from services.pump_service import calculate_pump

# Input values
weight = 5.0
species = 'cat'
propofol_pct = '1%'
target_dose = 0.2  # mg/kg/min
duration = 60  # minutes
asa = 'II'

# Propofol calculations
prop = calculate_propofol(weight, target_dose, duration, species, propofol_pct, asa)

# Pump calculations
propofol_ml = prop['required_ml']
total_mg = prop['total_mg']
diluent_ml = 40.0
line_primed = 'yes'
prime_fluid = 'suero'
dead_volume_ml = 15.0
pump = calculate_pump(propofol_ml, total_mg, diluent_ml, duration, line_primed, prime_fluid, dead_volume_ml)

print('PROP_CALC')
print(json.dumps(prop, indent=2, ensure_ascii=False))
print('PUMP_CALC')
print(json.dumps(pump, indent=2, ensure_ascii=False))
