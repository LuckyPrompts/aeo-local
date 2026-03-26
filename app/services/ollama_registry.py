import subprocess
from typing import List


def list_installed_models() -> List[str]:
    try:
        out = subprocess.check_output(["ollama", "list"], text=True)
    except FileNotFoundError:
        raise RuntimeError("ollama not found in PATH")

    lines = out.strip().splitlines()
    if len(lines) <= 1:
        return []

    models = []
    for line in lines[1:]:
        parts = line.split()
        if parts:
            models.append(parts[0].strip())

    return models
