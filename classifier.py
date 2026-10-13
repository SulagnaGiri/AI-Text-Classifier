
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()
API_KEY = os.getenv("NVIDIA_API_KEY")
API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"  # OpenAI-compatible
MODEL = "nvidia/nemotron-3-super-120b-a12b"
TIMEOUT_SECONDS = 90
BASE_DIR = Path(__file__).parent
TAXONOMY = json.loads((BASE_DIR / "categories.json").read_text(encoding="utf-8"))
PROMPT_TEMPLATE = (BASE_DIR / "prompts" / "classifier_prompt.txt").read_text(encoding="utf-8")

# Map every subcategory back to its category, e.g. "paper_jam" -> "hardware".
SUBCATEGORY_TO_CATEGORY = {
    sub: category
    for category, info in TAXONOMY["categories"].items()
    for sub in info["subcategories"]
}

RequestType = Literal[tuple(TAXONOMY["request_types"])]
Category = Literal[tuple(TAXONOMY["categories"])]
Subcategory = Literal[tuple(SUBCATEGORY_TO_CATEGORY)]
Device = Literal[tuple(TAXONOMY["affected_devices"])]
Priority = Literal[tuple(TAXONOMY["priorities"])]


class SupportDescription(BaseModel):
    request_type: RequestType
    category: Category
    subcategory: Subcategory = Field(description="Must be one of the subcategories of the chosen category.")
    affected_device: Device
    priority: Priority
    confidence: float = Field(ge=0.0, le=1.0)
    needs_clarification: bool
    reasoning: str


def _bullets(items: dict) -> str:
    return "\n".join(f"- {name}: {text}" for name, text in items.items())


def _format_categories() -> str:
    blocks = []
    for name, info in TAXONOMY["categories"].items():
        blocks.append(f"### {name}: {info['description']}\n{_bullets(info['subcategories'])}")
    return "\n\n".join(blocks)


def build_prompt(message: str) -> str:
    return PROMPT_TEMPLATE.format(
        request_types=_bullets(TAXONOMY["request_types"]),
        categories=_format_categories(),
        affected_devices=_bullets(TAXONOMY["affected_devices"]),
        priorities=_bullets(TAXONOMY["priorities"]),
        message=message,
    )


def _fallback(request_type: str, device: str, reasoning: str) -> dict:
    return {
        "request_type": request_type,
        "category": "other",
        "subcategory": "other",
        "affected_device": device,
        "priority": "low",
        "confidence": 1.0,
        "needs_clarification": request_type == "unclear",
        "reasoning": reasoning,
    }


def _enforce_rules(result: dict) -> dict:
    """Fix combinations the schema alone cannot prevent."""
    if result["request_type"] == "non_it_related":
        return {**_fallback("non_it_related", "none", result["reasoning"]), "confidence": result["confidence"]}
    if result["request_type"] == "unclear":
        return {**_fallback("unclear", "unknown", result["reasoning"]), "confidence": result["confidence"]}

    # Trust the more specific label: make category agree with subcategory.
    result["category"] = SUBCATEGORY_TO_CATEGORY[result["subcategory"]]
    if result["category"] == "other":
        result["needs_clarification"] = True
    return result


def _call_llm(prompt: str) -> str:
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 2048,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "classification", "schema": SupportDescription.model_json_schema()},
        },
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"HTTP {error.code}: {error.read().decode('utf-8', 'replace')[:200]}") from error
    return data["choices"][0]["message"]["content"]


def classify_message(message: str, retries: int = 2) -> dict:
    message = message.strip()
    if not message:
        return _fallback("unclear", "unknown", "Empty message.")

    last_error = None
    for attempt in range(retries + 1):
        try:
            result = SupportDescription.model_validate_json(_call_llm(build_prompt(message)))
            return _enforce_rules(result.model_dump())
        except Exception as error:
            last_error = error
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Classification failed after {retries + 1} attempts: {last_error}")


if __name__ == "__main__":
    message = input("Please enter the message you want to classify: ")
    result = classify_message(message)
    print(json.dumps(result, indent=2))
