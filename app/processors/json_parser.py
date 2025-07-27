import json

def read_summary_json(path: str) -> str:
    """Read and return pretty-printed JSON data."""
    with open(path, 'r') as f:
        data = json.load(f)
    return json.dumps(data, indent=2)
