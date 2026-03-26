from app.agents.intake_agent import load_profile
from app.agents.evaluation_agent import run_evaluation

def run(profile_path: str) -> dict:
    profile = load_profile(profile_path)

    # placeholder until content agent is split out
    from generate_site_local import build_site_html

    html = build_site_html(profile)
    evaluation = run_evaluation(html)

    return {
        "profile": profile,
        "html": html,
        "evaluation": evaluation,
    }
