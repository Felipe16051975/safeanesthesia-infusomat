import json, importlib.util
module_path = r"C:/Users/felip/.gemini/antigravity-ide/scratch/safeanesthesia-infusomat-module/services/pump_service.py"
spec = importlib.util.spec_from_file_location("pump_service", module_path)
pump = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pump)
result = pump.calculate_pump(
    volume_final=46,
    flow_ml_h=46,
    vtbi_ml=46,
    time_min=60,
    dead_volume_ml=5,
    line_primed="si",
    primed_with="suero"
)
print(json.dumps(result, ensure_ascii=False, indent=2))
