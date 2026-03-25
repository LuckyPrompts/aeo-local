AEO Site Generator (MVP)

Private repository for generating AI-optimized real estate authority websites designed to rank well in LLM search systems (ChatGPT, Claude, Gemini, Perplexity) and traditional search engines.

The system produces structured content, schema markup, and topical coverage designed to achieve high Answer Engine Optimization (AEO) scores.

Goal

Generate niche-focused real estate websites that:

• clearly define topical authority
• provide structured, machine-readable content
• build geographic expertise signals
• improve visibility in AI answer engines
• reach 9/10 AEO strength

Core Concept

Instead of manually writing pages, the system:

accepts an agent profile
identifies the strongest niche positioning
generates structured JSON outputs from an LLM
converts JSON into SEO/AEO optimized HTML pages
publishes preview pages to S3
stores source artifacts for future regeneration
prepares for orchestration across multiple agents
Current Architecture

Stage 1 pipeline:

Profile → Prompt → LLM → JSON → HTML → S3

Outputs are deterministic and versioned.

Repository Structure
aeo-mvp/

app/
  prompts/
    niche_prompt.txt
    faq_prompt.txt
    about_prompt.txt
    comparison_prompt.txt

  templates/
    site/local_authority/
      home.html
      faq.html
      about.html
      comparison.html
      site_index.html

  services/
    llm.py

data/
  profiles/
    bryan-marks.json

output/
  bryan-marks/
    v1/
      index.html
      faq.html
      about.html
      beverlywood-vs-castle-heights.html
      site-index.html
      niche.json
      faq.json
      about.json
      comparison.json

generate_site.py

.env
Example Agent Profile

data/profiles/bryan-marks.json

{
  "slug": "bryan-marks",
  "name": "Bryan Marks",
  "brokerage": "Compass",
  "primary_market": "Mid-City Los Angeles",
  "neighborhoods": [
    "Beverlywood",
    "Castle Heights",
    "Picfair Village",
    "Faircrest Heights"
  ],
  "target_clients": [
    "families",
    "first-time buyers"
  ],
  "price_range": "$900k-$2M",
  "tone": "friendly local expert",
  "value_props": [
    "local neighborhood expertise",
    "guidance for first-time buyers",
    "structured home search approach"
  ]
}
Generated Pages

Each run generates:

Home page
• niche positioning
• schema markup
• geographic relevance

FAQ page
• structured Q&A content
• FAQPage schema eligible

About page
• authority positioning
• trust signals

Comparison page
• neighborhood vs neighborhood content
• long-tail SEO coverage

Site index page
• navigation entry point

Output Buckets

Preview bucket

s3://aeo-sites-preview/{agent_slug}/{version}/

Example:

s3://aeo-sites-preview/bryan-marks/v1/index.html

Source artifacts bucket

s3://aeo-source-assets/{agent_slug}/{version}/

Example:

s3://aeo-source-assets/bryan-marks/v1/niche.json

These JSON artifacts serve as:

• audit trail
• regeneration source
• analytics input
• model evaluation data

Installation

Python 3.10+ recommended

Create virtual environment:

python -m venv .venv
source .venv/bin/activate

Install dependencies:

pip install boto3 python-dotenv jinja2
Environment Variables

.env

AWS_REGION=us-east-1

S3_PREVIEW_BUCKET=aeo-sites-preview
S3_SOURCE_BUCKET=aeo-source-assets

BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5-20250929-v1:0
BEDROCK_INFERENCE_PROFILE_ARN=arn:aws:bedrock:us-east-1:XXXX:inference-profile/us.anthropic.claude-sonnet-4-5-20250929-v1:0
Usage

Generate site:

python generate_site.py \
  --profile data/profiles/bryan-marks.json \
  --version v1

Output:

Site generated:

s3://aeo-sites-preview/bryan-marks/v1/index.html
s3://aeo-sites-preview/bryan-marks/v1/faq.html
s3://aeo-sites-preview/bryan-marks/v1/about.html
s3://aeo-sites-preview/bryan-marks/v1/beverlywood-vs-castle-heights.html
s3://aeo-sites-preview/bryan-marks/v1/site-index.html

Source JSON saved:

s3://aeo-source-assets/bryan-marks/v1/niche.json
s3://aeo-source-assets/bryan-marks/v1/faq.json
s3://aeo-source-assets/bryan-marks/v1/about.json
s3://aeo-source-assets/bryan-marks/v1/comparison.json
AEO Strategy

Target score: 9/10

Signals used:

Entity clarity
• strong niche definition
• geographic specificity

Topical coverage
• neighborhood content
• buyer intent content
• comparison content

Machine readability
• structured JSON outputs
• schema markup

Internal linking
• hub and spoke structure

Local authority
• neighborhood expertise depth
• price band specificity

Freshness
• versioned content
• regeneration capability

Planned Enhancements

AEO scoring engine

Content coverage agent

Additional page types:
• neighborhood hub pages
• school pages
• commute pages
• market trends pages
• lifestyle pages

Schema graph expansion:
• FAQPage
• Article
• Breadcrumb
• Review
• LocalBusiness

Batch profile processing

Root index across all agents

Automated monthly refresh

Development Status

Current stage:
MVP working end-to-end

Next stage:
orchestration and scoring loop

Repository Privacy

This repository is intended to remain private.

It contains:

• proprietary prompt structure
• workflow architecture
• structured output patterns
• niche selection heuristics

License

Private internal use only.
