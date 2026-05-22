import json
import os

def load_config() -> dict:
    """Load the clinical limits configuration JSON.

    Returns a dict with the content of `config/clinical_limits.json`.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    config_path = os.path.join(base_dir, 'config', 'clinical_limits.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)
