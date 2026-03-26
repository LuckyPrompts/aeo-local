import os
import json
import argparse
import re
import traceback
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from ollama import Client


DEFAULT_MODEL = "qwen3.5:9b"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

BASE_DIR = Path(__file__).parent
TEMPLATE_DIR = BASE_DIR / "app" / "templates" / "site" / "local_authority"
OUTPUT_DIR = BASE_DIR / "output"
DEBUG_DIR = BASE_DIR / "debug"

OUTPUT_DIR.mkdir(exist_ok=True)
DEBUG_DIR.mkdir(exist_ok=True)


###########################################
# LLM
###########################################

class OllamaLLM:
    def __init__(self, model=DEFAULT_MODEL):
        self.client = Client(host=OLLAMA_HOST)
        self.model = model

    def generate(self, prompt, max_tokens=2000):
        response = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate structured marketing website content."
                        " Return valid JSON only."
                        " Do not include markdown code fences."
                        " Do not include explanation."
                        " Do not include any text before or after the JSON."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "temperature": 0,
                "num_predict": max_tokens
            }
        )
        return response["message"]["content"]


###########################################
# PARSE
###########################################

def repair_json(text):
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    return text


def parse_json(text):
    if not text:
        raise ValueError("EMPTY_RESPONSE")

    closing_tag = "</" + "think" + ">"
    if closing_tag in text:
        text = text.split(closing_tag, 1)[-1]

    text = re.sub(r"```(?:json)?", "", text)
    text = text.replace("```", "").strip()

    if not text:
        raise ValueError("EMPTY_RESPONSE")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
            try:
                return json.loads(repair_json(candidate))
            except json.JSONDecodeError:
                pass

    raise ValueError("JSON_PARSE_FAILED")


###########################################
# UTILITIES
###########################################

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def render_html(template_name, context, out_path):
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False
    )
    template = env.get_template(template_name)
    html = template.render(**context)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  rendered → {out_path.name}")


###########################################
# PROMPTS
###########################################

def home_prompt(profile):
    return f"""
Create homepage content for a hyperlocal real estate expert.

Profile:
{json.dumps(profile, indent=2)}

Return JSON with exactly these fields:

{{
  "niche_title": "",
  "intro": "",
  "about": "",
  "neighborhoods": []
}}
"""


def faq_prompt(profile):
    return f"""
Generate 5 SEO optimized FAQs for this real estate niche.

Profile:
{json.dumps(profile, indent=2)}

Rules:
- Return a JSON object with a faqs array
- Keep each answer under 60 words

{{
  "faqs": [
    {{
      "question": "",
      "answer": ""
    }}
  ]
}}
"""


def about_prompt(profile):
    return f"""
Create an about page for this real estate expert.

Profile:
{json.dumps(profile, indent=2)}

Rules:
- Return JSON only
- Keep bio under 50 words
- Keep why_work_with_me under 50 words

Return JSON with exactly these fields:

{{
  "headline": "",
  "bio": "",
  "why_work_with_me": "",
  "cta": ""
}}
"""


def comparison_prompt(profile):
    neighborhoods = profile.get("neighborhoods", [])
    a = neighborhoods[0] if len(neighborhoods) > 0 else "Neighborhood A"
    b = neighborhoods[1] if len(neighborhoods) > 1 else "Neighborhood B"

    return f"""
Create a neighborhood comparison page for a real estate expert.

Profile:
{json.dumps(profile, indent=2)}

Compare {a} vs {b}.

Rules:
- Return JSON only
- key_differences should be a list of 4 short strings
- faq should be a list of 3 question/answer pairs

Return JSON with exactly these fields:

{{
  "title": "",
  "summary": "",
  "neighborhood_a": "{a}",
  "neighborhood_b": "{b}",
  "neighborhood_a_best_for": "",
  "neighborhood_b_best_for": "",
  "key_differences": [],
  "faq": [
    {{
      "question": "",
      "answer": ""
    }}
  ]
}}
"""


###########################################
# DEBUG
###########################################

def save_debug_report(report):
    ts = report["ts"]
    path = DEBUG_DIR / f"debug_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return path


def print_paste_summary(report, debug_path):
    print("\n" + "=" * 60)
    print("PASTE THIS TO CLAUDE")
    print("=" * 60)
    for step in report["steps"]:
        status = "OK" if step["success"] else "FAILED"
        print(f"\n[{status}] {step['name']}")
        if not step["success"]:
            print(f"  Error          : {step['error']}")
            print(f"  Raw length     : {step['raw_length']} chars")
            print(f"  Raw tail       :\n{step['raw_tail']}")
    print(f"\nModel      : {report['model']}")
    print(f"Profile    : {report['profile']}")
    print(f"Debug file : {debug_path}")
    print("=" * 60 + "\n")


###########################################
# RUNNER
###########################################

def run_step(name, llm, prompt_fn, profile, max_tokens):
    step = {
        "name": name,
        "success": False,
        "error": None,
        "traceback": None,
        "raw_length": 0,
        "raw_tail": "",
        "max_tokens": max_tokens,
    }
    raw = ""
    try:
        print(f"  [{name}] generating...")
        raw = llm.generate(prompt_fn(profile), max_tokens=max_tokens)
        step["raw_length"] = len(raw)
        step["raw_tail"] = raw[-400:] if len(raw) > 400 else raw
        result = parse_json(raw)
        step["success"] = True
        print(f"  [{name}] OK — {len(raw)} chars")
        return result, step
    except Exception as e:
        step["error"] = str(e)
        step["traceback"] = traceback.format_exc()
        step["raw_length"] = len(raw)
        step["raw_tail"] = raw[-400:] if len(raw) > 400 else raw
        print(f"  [{name}] FAILED — {e}")
        return None, step


###########################################
# SCHEMA BUILDER
###########################################

def build_schema(profile, home_data):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "RealEstateAgent",
        "name": profile.get("name"),
        "description": home_data.get("intro"),
        "areaServed": profile.get("neighborhoods", []),
        "priceRange": profile.get("price_range"),
        "memberOf": {
            "@type": "Organization",
            "name": profile.get("brokerage")
        }
    }, indent=2)


###########################################
# GENERATE
###########################################

def generate_site(profile_path, version, model):

    llm = OllamaLLM(model=model)
    profile = load_json(profile_path)

    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    report = {
        "ts": ts,
        "model": model,
        "profile": str(profile_path),
        "version": version,
        "steps": []
    }

    steps_config = [
        ("home",       home_prompt,       2000),
        ("faq",        faq_prompt,        3000),
        ("about",      about_prompt,      2000),
        ("comparison", comparison_prompt, 3000),
    ]

    results = {}

    print(f"\nStarting generation — model: {model}\n")

    for name, prompt_fn, max_tokens in steps_config:
        result, step = run_step(name, llm, prompt_fn, profile, max_tokens)
        report["steps"].append(step)
        if result is not None:
            results[name] = result

    any_failed = any(not s["success"] for s in report["steps"])

    if results:
        out_dir = OUTPUT_DIR / version / ts
        out_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON artifacts
        for name, data in results.items():
            save_json(out_dir / f"{name}.json", data)

        # Render HTML pages
        neighborhoods = profile.get("neighborhoods", [])
        a = neighborhoods[0] if len(neighborhoods) > 0 else "Neighborhood A"
        b = neighborhoods[1] if len(neighborhoods) > 1 else "Neighborhood B"
        slug_a = a.lower().replace(" ", "-")
        slug_b = b.lower().replace(" ", "-")
        comparison_filename = f"{slug_a}-vs-{slug_b}.html"

        pages = [
            {"label": "Home",       "url": "index.html"},
            {"label": "FAQ",        "url": "faq.html"},
            {"label": "About",      "url": "about.html"},
            {"label": "Comparison", "url": comparison_filename},
        ]

        if "home" in results:
            render_html("home.html", {
                "niche_title":   results["home"].get("niche_title", ""),
                "intro":         results["home"].get("intro", ""),
                "about":         results["home"].get("about", ""),
                "neighborhoods": results["home"].get("neighborhoods", profile.get("neighborhoods", [])),
                "name":          profile.get("name", ""),
                "schema":        build_schema(profile, results["home"]),
            }, out_dir / "index.html")

        if "faq" in results:
            render_html("faq.html", {
                "faqs": results["faq"].get("faqs", results["faq"])
            }, out_dir / "faq.html")

        if "about" in results:
            render_html("about.html", {
                "headline":        results["about"].get("headline", ""),
                "bio":             results["about"].get("bio", ""),
                "why_work_with_me": results["about"].get("why_work_with_me", ""),
                "cta":             results["about"].get("cta", ""),
            }, out_dir / "about.html")

        if "comparison" in results:
            render_html("comparison.html",
                results["comparison"],
                out_dir / comparison_filename
            )

        render_html("site_index.html", {
            "agent_name":    profile.get("name", ""),
            "primary_niche": profile.get("primary_market", ""),
            "pages":         pages,
        }, out_dir / "site-index.html")

        print(f"\nSaved to: {out_dir}")

    debug_path = save_debug_report(report)

    if any_failed:
        print_paste_summary(report, debug_path)
    else:
        print("\nAll steps succeeded.")
        print(f"Debug log: {debug_path}")


###########################################
# CLI
###########################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--version", default="local-test")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    generate_site(
        profile_path=args.profile,
        version=args.version,
        model=args.model
    )
