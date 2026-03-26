import json
from ollama import Client


class OllamaLLM:
    def __init__(self, model: str = "qwen3.5:9b", host: str = "http://localhost:11434"):
        self.model = model
        self.client = Client(host=host)

    def generate(self, prompt: str, max_tokens: int = 1200) -> str:
        response = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise content generator. "
                        "Return valid JSON only. Do not wrap output in markdown fences."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            options={
                "num_predict": max_tokens,
                "temperature": 0.2,
            },
        )
        return response["message"]["content"]
