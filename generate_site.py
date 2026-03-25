import argparse
import json
import os
from pathlib import Path

import boto3
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

from app.services.llm import BedrockLLM

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "app" / "templates"
NICHE_PROMPT_FILE = BASE_DIR / "app" / "prompts" / "niche_prompt.txt"
FAQ_PROMPT_FILE = BASE_DIR / "app" / "prompts" / "faq_prompt.txt"
ABOUT_PROMPT_FILE = BASE_DIR / "app" / "prompts" / "about_prompt.txt"
COMPARISON_PROMPT_FILE = BASE_DIR / "app" / "prompts" / "comparison_prompt.txt"
OUTPUT_DIR = BASE_DIR / "output"

env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
home_template = env.get_template("site/local_authority/home.html")
faq_template = env.get_template("site/local_authority/faq.html")
about_template = env.get_template("site/local_authority/about.html")
comparison_template = env.get_template("site/local_authority/comparison.html")
site_index_template = env.get_template("site/local_authority/site_index.html")


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        required=True,
        help="Path to agent profile JSON, e.g. data/profiles/bryan-marks.json",
    )
    parser.add_argument(
        "--version",
        default="v1",
        help="Site version label, e.g. v1 or 2026-03-25",
    )
    return parser.parse_args()


def strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def load_json_file(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_text_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_json_response(raw: str):
    cleaned = strip_code_fences(raw)
    try:
        return json.loads(cleaned), cleaned
    except json.JSONDecodeError:
        print("LLM did not return valid JSON")
        print(cleaned)
        raise


def render_and_write(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def write_json_file(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def upload_file_to_s3(s3_client, local_path: Path, bucket: str, key: str, content_type: str) -> None:
    s3_client.upload_file(
        str(local_path),
        bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )


def upload_json_to_s3(s3_client, data: dict, bucket: str, key: str) -> None:
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def build_homepage(profile: dict, llm: BedrockLLM):
    prompt_template = load_text_file(NICHE_PROMPT_FILE)
    prompt = prompt_template.format(
        name=profile["name"],
        brokerage=profile["brokerage"],
        primary_market=profile["primary_market"],
        neighborhoods=", ".join(profile["neighborhoods"]),
        target_clients=", ".join(profile["target_clients"]),
        price_range=profile["price_range"],
        tone=profile["tone"],
        value_props=", ".join(profile["value_props"]),
    )

    raw = llm.generate(prompt, max_tokens=900)
    niche_data, cleaned_raw = parse_json_response(raw)

    primary_niche = niche_data.get("primary_niche", "").strip()
    backup_niche = niche_data.get("backup_niche", "").strip()
    rationale = niche_data.get("rationale", "").strip()
    intro = niche_data.get("intro", "").strip()

    if not primary_niche:
        primary_niche = f"{profile['primary_market']} Real Estate Expert"

    if not intro:
        intro = f"Specializing in homes in {profile['primary_market']}."

    about = (
        f"{profile['name']} helps {', '.join(profile['target_clients'])} "
        f"find homes in {profile['primary_market']}."
    )

    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "RealEstateAgent",
            "name": profile["name"],
            "areaServed": profile["primary_market"],
            "worksFor": profile["brokerage"],
            "description": primary_niche,
        }
    )

    html = home_template.render(
        niche_title=primary_niche,
        intro=intro,
        about=about,
        neighborhoods=profile["neighborhoods"],
        name=profile["name"],
        schema=schema,
    )

    metadata = {
        "primary_niche": primary_niche,
        "backup_niche": backup_niche,
        "rationale": rationale,
        "intro": intro,
        "raw_llm_output": cleaned_raw,
    }

    return html, metadata


def build_faq_page(profile: dict, primary_niche: str, llm: BedrockLLM):
    prompt_template = load_text_file(FAQ_PROMPT_FILE)
    prompt = prompt_template.format(
        name=profile["name"],
        primary_niche=primary_niche,
        primary_market=profile["primary_market"],
        neighborhoods=", ".join(profile["neighborhoods"]),
        target_clients=", ".join(profile["target_clients"]),
        tone=profile["tone"],
    )

    raw = llm.generate(prompt, max_tokens=1400)
    faq_data, cleaned_raw = parse_json_response(raw)

    if not isinstance(faq_data, list):
        raise ValueError("FAQ response was not a JSON array")

    faqs = []
    for item in faq_data:
        if isinstance(item, dict):
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            if question and answer:
                faqs.append({"question": question, "answer": answer})

    if not faqs:
        raise ValueError("No valid FAQ items were returned by the LLM")

    html = faq_template.render(
        niche_title=primary_niche,
        faqs=faqs,
    )

    metadata = {
        "faq_count": len(faqs),
        "faqs": faqs,
        "raw_llm_output": cleaned_raw,
    }

    return html, metadata


def build_about_page(profile: dict, primary_niche: str, llm: BedrockLLM):
    prompt_template = load_text_file(ABOUT_PROMPT_FILE)
    prompt = prompt_template.format(
        name=profile["name"],
        brokerage=profile["brokerage"],
        primary_niche=primary_niche,
        primary_market=profile["primary_market"],
        neighborhoods=", ".join(profile["neighborhoods"]),
        target_clients=", ".join(profile["target_clients"]),
        tone=profile["tone"],
        value_props=", ".join(profile["value_props"]),
    )

    raw = llm.generate(prompt, max_tokens=1000)
    about_data, cleaned_raw = parse_json_response(raw)

    headline = about_data.get("headline", "").strip() or f"About {profile['name']}"
    bio = about_data.get("bio", "").strip()
    why_work = about_data.get("why_work_with_me", "").strip()
    cta = about_data.get("cta", "").strip() or "Contact me to start your home search."

    html = about_template.render(
        name=profile["name"],
        headline=headline,
        bio=bio,
        why_work_with_me=why_work,
        cta=cta,
    )

    metadata = {
        "headline": headline,
        "bio": bio,
        "why_work_with_me": why_work,
        "cta": cta,
        "raw_llm_output": cleaned_raw,
    }

    return html, metadata


def build_comparison_page(profile: dict, primary_niche: str, llm: BedrockLLM):
    neighborhood_a = profile["neighborhoods"][0]
    neighborhood_b = profile["neighborhoods"][1]

    prompt_template = load_text_file(COMPARISON_PROMPT_FILE)
    prompt = prompt_template.format(
        name=profile["name"],
        primary_niche=primary_niche,
        primary_market=profile["primary_market"],
        neighborhood_a=neighborhood_a,
        neighborhood_b=neighborhood_b,
        target_clients=", ".join(profile["target_clients"]),
        tone=profile["tone"],
    )

    raw = llm.generate(prompt, max_tokens=1600)
    comparison_data, cleaned_raw = parse_json_response(raw)

    title = comparison_data.get("title", "").strip() or f"{neighborhood_a} vs {neighborhood_b}"
    summary = comparison_data.get("summary", "").strip()
    neighborhood_a_best_for = comparison_data.get("neighborhood_a_best_for", "").strip()
    neighborhood_b_best_for = comparison_data.get("neighborhood_b_best_for", "").strip()
    key_differences = comparison_data.get("key_differences", [])
    faq = comparison_data.get("faq", [])

    if not isinstance(key_differences, list):
        key_differences = []

    if not isinstance(faq, list):
        faq = []

    html = comparison_template.render(
        title=title,
        summary=summary,
        neighborhood_a=neighborhood_a,
        neighborhood_b=neighborhood_b,
        neighborhood_a_best_for=neighborhood_a_best_for,
        neighborhood_b_best_for=neighborhood_b_best_for,
        key_differences=key_differences,
        faq=faq,
    )

    metadata = {
        "title": title,
        "summary": summary,
        "neighborhood_a_best_for": neighborhood_a_best_for,
        "neighborhood_b_best_for": neighborhood_b_best_for,
        "key_differences": key_differences,
        "faq": faq,
        "raw_llm_output": cleaned_raw,
    }

    slug = f"{neighborhood_a.lower().replace(' ', '-')}-vs-{neighborhood_b.lower().replace(' ', '-')}.html"

    return html, metadata, slug


def build_site_index(profile: dict, primary_niche: str, comparison_title: str, comparison_slug: str):
    pages = [
        {"label": "Home", "href": "index.html"},
        {"label": "FAQ", "href": "faq.html"},
        {"label": "About", "href": "about.html"},
        {"label": comparison_title, "href": comparison_slug},
    ]

    html = site_index_template.render(
        agent_name=profile["name"],
        primary_niche=primary_niche,
        pages=pages,
    )

    return html


def main():
    args = get_args()

    profile_path = Path(args.profile)
    profile = load_json_file(profile_path)

    site_version = args.version
    agent_slug = profile.get("slug") or profile["name"].lower().replace(" ", "-")
    agent_output_dir = OUTPUT_DIR / agent_slug / site_version
    agent_output_dir.mkdir(parents=True, exist_ok=True)

    llm = BedrockLLM()
    s3 = boto3.client("s3")

    preview_bucket = os.getenv("S3_PREVIEW_BUCKET")
    source_bucket = os.getenv("S3_SOURCE_BUCKET")

    if not preview_bucket:
        raise ValueError("S3_PREVIEW_BUCKET is not set in .env")

    if not source_bucket:
        raise ValueError("S3_SOURCE_BUCKET is not set in .env")

    # Homepage
    home_html, niche_metadata = build_homepage(profile, llm)
    home_output_path = agent_output_dir / "index.html"
    render_and_write(home_output_path, home_html)
    write_json_file(agent_output_dir / "niche.json", niche_metadata)

    home_key = f"{agent_slug}/{site_version}/index.html"
    niche_key = f"{agent_slug}/{site_version}/niche.json"

    upload_file_to_s3(s3, home_output_path, preview_bucket, home_key, "text/html")
    upload_json_to_s3(s3, niche_metadata, source_bucket, niche_key)

    # FAQ
    faq_html, faq_metadata = build_faq_page(profile, niche_metadata["primary_niche"], llm)
    faq_output_path = agent_output_dir / "faq.html"
    render_and_write(faq_output_path, faq_html)
    write_json_file(agent_output_dir / "faq.json", faq_metadata)

    faq_key = f"{agent_slug}/{site_version}/faq.html"
    faq_json_key = f"{agent_slug}/{site_version}/faq.json"

    upload_file_to_s3(s3, faq_output_path, preview_bucket, faq_key, "text/html")
    upload_json_to_s3(s3, faq_metadata, source_bucket, faq_json_key)

    # About
    about_html, about_metadata = build_about_page(profile, niche_metadata["primary_niche"], llm)
    about_output_path = agent_output_dir / "about.html"
    render_and_write(about_output_path, about_html)
    write_json_file(agent_output_dir / "about.json", about_metadata)

    about_key = f"{agent_slug}/{site_version}/about.html"
    about_json_key = f"{agent_slug}/{site_version}/about.json"

    upload_file_to_s3(s3, about_output_path, preview_bucket, about_key, "text/html")
    upload_json_to_s3(s3, about_metadata, source_bucket, about_json_key)

    # Comparison
    comparison_html, comparison_metadata, comparison_slug = build_comparison_page(
        profile, niche_metadata["primary_niche"], llm
    )
    comparison_output_path = agent_output_dir / comparison_slug
    render_and_write(comparison_output_path, comparison_html)
    write_json_file(agent_output_dir / "comparison.json", comparison_metadata)

    comparison_key = f"{agent_slug}/{site_version}/{comparison_slug}"
    comparison_json_key = f"{agent_slug}/{site_version}/comparison.json"

    upload_file_to_s3(s3, comparison_output_path, preview_bucket, comparison_key, "text/html")
    upload_json_to_s3(s3, comparison_metadata, source_bucket, comparison_json_key)

    # Site index
    site_index_html = build_site_index(
        profile,
        niche_metadata["primary_niche"],
        comparison_metadata["title"],
        comparison_slug,
    )
    site_index_output_path = agent_output_dir / "site-index.html"
    render_and_write(site_index_output_path, site_index_html)

    site_index_key = f"{agent_slug}/{site_version}/site-index.html"
    upload_file_to_s3(s3, site_index_output_path, preview_bucket, site_index_key, "text/html")

    print("Site generated:")
    print(f"s3://{preview_bucket}/{home_key}")
    print(f"s3://{preview_bucket}/{faq_key}")
    print(f"s3://{preview_bucket}/{about_key}")
    print(f"s3://{preview_bucket}/{comparison_key}")
    print(f"s3://{preview_bucket}/{site_index_key}")
    print()
    print("Source JSON saved:")
    print(f"s3://{source_bucket}/{niche_key}")
    print(f"s3://{source_bucket}/{faq_json_key}")
    print(f"s3://{source_bucket}/{about_json_key}")
    print(f"s3://{source_bucket}/{comparison_json_key}")
    print()
    print(json.dumps({"primary_niche": niche_metadata["primary_niche"]}, indent=2))
    print(json.dumps({"faq_count": faq_metadata["faq_count"]}, indent=2))


if __name__ == "__main__":
    main()
