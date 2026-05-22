import json, importlib.util, os

# Load pump_service module
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'services', 'pump_service.py'))
spec = importlib.util.spec_from_file_location('pump_service', module_path)
pump = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pump)

def run_test(volume_final, flow_ml_h, vtbi_ml, time_min, dead_volume_ml, line_primed, primed_with):
    result = pump.calculate_pump(
        volume_final=volume_final,
        flow_ml_h=flow_ml_h,
        vtbi_ml=vtbi_ml,
        time_min=time_min,
        dead_volume_ml=dead_volume_ml,
        line_primed=line_primed,
        primed_with=primed_with,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    print('--- Suero test ---')
    run_test(46, 46, 46, 60, 5, 'si', 'suero')
    print('--- Mezcla test ---')
    run_test(46, 46, 46, 60, 5, 'si', 'mezcla')
