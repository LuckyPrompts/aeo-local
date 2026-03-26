from typing import Optional

from app.config.model_policy import PREFERRED_MODELS, STEP_TASK_MAP
from app.services.ollama_registry import list_installed_models
from app.services.universal_model_router import route_key


def route_for_step(step_name: str, override: Optional[str] = None):
    installed_models = list_installed_models()
    return route_key(
        key=step_name,
        key_to_task_map=STEP_TASK_MAP,
        preferred_models=PREFERRED_MODELS,
        installed_models=installed_models,
        override=override,
    )
