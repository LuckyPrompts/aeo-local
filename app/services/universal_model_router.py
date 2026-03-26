from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class ModelSelection:
    key: str
    task_type: str
    model: str
    reason: str


def resolve_model_for_task(task_type: str, installed_models: List[str], preferred_models: Dict) -> Tuple[str, str]:
    candidates = preferred_models.get(task_type, preferred_models.get("fallback", []))

    for candidate in candidates:
        if candidate in installed_models:
            return candidate, f"installed preferred model for task_type={task_type}"

    fallback_candidates = preferred_models.get("fallback", [])
    for candidate in fallback_candidates:
        if candidate in installed_models:
            return candidate, f"fallback installed model for task_type={task_type}"

    raise RuntimeError(
        f"No suitable installed model found for task_type={task_type}. "
        f"Installed models: {installed_models}"
    )


def route_key(
    key: str,
    key_to_task_map: Dict,
    preferred_models: Dict,
    installed_models: List[str],
    override: Optional[str] = None,
) -> ModelSelection:
    key = (key or "").strip().lower()

    if override:
        return ModelSelection(
            key=key,
            task_type="manual_override",
            model=override,
            reason="manual override from caller",
        )

    task_type = key_to_task_map.get(key, "fallback")
    model, reason = resolve_model_for_task(
        task_type=task_type,
        installed_models=installed_models,
        preferred_models=preferred_models,
    )

    return ModelSelection(
        key=key,
        task_type=task_type,
        model=model,
        reason=reason,
    )
