PREFERRED_MODELS = {
    "content_light": ["mistral:7b", "qwen2.5:7b", "qwen3.5:9b"],
    "evaluation": ["gemma3:1b", "phi3:mini", "mistral:7b"],
    "planning": ["qwen3.5:9b", "mistral:7b"],
    "vision": ["llava:7b", "qwen2.5-vl:7b"],
    "fallback": ["mistral:7b", "qwen3.5:9b", "gemma3:1b"],
}

STEP_TASK_MAP = {
    "home": "content_light",
    "faq": "content_light",
    "about": "content_light",
    "comparison": "content_light",
    "aeo_evaluation": "evaluation",
    "planner": "planning",
    "vision_scan": "vision",
}
