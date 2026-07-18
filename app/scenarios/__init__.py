"""Scenario loading for GlassBox Sentinel."""

import json
from pathlib import Path
from typing import Optional, Dict, Any

SCENARIOS_DIR = Path(__file__).parent.parent.parent / "fixtures"


def load_scenario(scenario_id: str) -> Optional[Dict[str, Any]]:
    """Load a scenario from a JSON fixture file."""
    # Try to find the scenario file
    scenario_file = SCENARIOS_DIR / f"{scenario_id}.json"
    
    if not scenario_file.exists():
        # Try with scenario_ prefix
        scenario_file = SCENARIOS_DIR / f"scenario_{scenario_id}.json"
    
    if not scenario_file.exists():
        return None
    
    with open(scenario_file, 'r') as f:
        return json.load(f)


def get_available_scenarios() -> list:
    """Get list of available scenario IDs."""
    scenarios = []
    for f in SCENARIOS_DIR.glob("*.json"):
        if f.name.startswith("scenario_"):
            scenario_id = f.name[9:-5]  # Remove 'scenario_' prefix and '.json'
        else:
            scenario_id = f.name[:-5]  # Remove '.json'
        
        # Load to verify it's valid
        with open(f, 'r') as fh:
            data = json.load(fh)
            if 'id' in data:
                scenario_id = data['id']
        
        scenarios.append({
            'id': scenario_id,
            'description': data.get('description', ''),
        })
    return scenarios
