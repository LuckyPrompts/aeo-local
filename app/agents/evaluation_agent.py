from app.services.aeo_evaluator import evaluate_html

def run_evaluation(html: str) -> dict:
    return evaluate_html(html)
