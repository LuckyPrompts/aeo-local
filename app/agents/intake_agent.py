from pathlib import Path
import json

def load_profile(profile_path: str) -> dict:
    path = Path(profile_path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
