import json
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

model_id = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

prompt = """
Recommend a niche for a real estate agent working in Mid-City Los Angeles,
including Beverlywood, Castle Heights, Picfair Village, and Faircrest Heights,
focused on families and first-time buyers.

Return:
1. Primary niche
2. Backup niche
3. One-sentence rationale
"""

body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 500,
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt}
            ]
        }
    ]
}

response = client.invoke_model(
    modelId=model_id,
    body=json.dumps(body),
    contentType="application/json",
    accept="application/json"
)

result = json.loads(response["body"].read())
print(result["content"][0]["text"])
