def evaluate_html(html: str) -> dict:
    score = 0
    suggestions = []

    checks = {
        "has_title": "<title>" in html,
        "has_meta_description": 'name="description"' in html,
        "has_h1": "<h1" in html,
        "has_schema": '"@context"' in html or "application/ld+json" in html,
        "has_faq": "faq" in html.lower(),
        "has_neighborhood_terms": any(x in html.lower() for x in ["neighborhood", "schools", "commute", "local"]),
        "has_contact_cta": any(x in html.lower() for x in ["contact", "call", "email", "schedule"]),
    }

    for passed in checks.values():
        if passed:
            score += 1

    if not checks["has_schema"]:
        suggestions.append("Add JSON-LD schema aligned to visible page content.")
    if not checks["has_faq"]:
        suggestions.append("Add FAQ content answering local buyer and seller questions.")
    if not checks["has_neighborhood_terms"]:
        suggestions.append("Increase neighborhood-specific authority content.")
    if not checks["has_contact_cta"]:
        suggestions.append("Add a stronger local contact call to action.")

    return {
        "score": round((score / len(checks)) * 10, 1),
        "checks": checks,
        "suggestions": suggestions,
    }
