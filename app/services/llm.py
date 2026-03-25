import json
import boto3

class BedrockLLM:
    def __init__(self, region_name="us-east-1", model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0"):
        self.client = boto3.client("bedrock-runtime", region_name=region_name)
        self.model_id = model_id

    def generate(self, prompt: str, max_tokens: int = 800) -> str:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        }

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        result = json.loads(response["body"].read())
        return result["content"][0]["text"]
