import os

from openai import OpenAI
from dotenv import load_dotenv
import json
import re

load_dotenv()

ANALYSIS_MODEL = "gpt-4o-mini"
GENERATION_MODEL = "gpt-4o-mini"


def fallback_response():
    return """
    {
      "attack_stage": "unknown",
      "intent": "unknown",
      "confidence": 0.0,
      "reasoning": ["LLM unavailable or failed"]
    }
    """


def clean_llm_output(text: str | None) -> str:
    if not text:
        return ""

    # Remove think blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\[think\].*?\[/think\]", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove markdown fences
    text = re.sub(r"```[a-zA-Z]*", "", text)
    text = text.replace("```", "")

    # Remove common wrappers
    text = re.sub(
        r"^(Here is the improved content:|Improved content:|Final output:|Output:)\s*",
        "",
        text.strip(),
        flags=re.IGNORECASE
    )

    return text.strip()


def _client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def call_llm(prompt, temperature=0.2, max_tokens=1200, mode="generation"):
    client = _client()

    if not client:
        print("OPENAI_API_KEY not set, using fallback")
        return fallback_response()

    model = GENERATION_MODEL if mode == "generation" else ANALYSIS_MODEL

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only the requested output. "
                        "Do not include reasoning, markdown, explanations, "
                        "analysis, <think> tags, or extra commentary."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        raw = response.choices[0].message.content
        return clean_llm_output(raw)

    except Exception as e:
        print("OpenAI Error:", e)
        return fallback_response()

def call_openai_strategy_llm(prompt: str, model: str = "gpt-4o-mini") -> str:
    """
    OpenAI call for Strategy Agent — strict JSON object responses.
    Raises on missing key or API errors (caller handles fallback).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You emit only one JSON object per request. No markdown, no explanations.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.15,
        max_tokens=4096,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("empty OpenAI response")
    return content
    
def call_llm_json(prompt, temperature=0.1, max_tokens=800, mode="analysis"):
    raw = call_llm(prompt, temperature=temperature, max_tokens=max_tokens, mode=mode)

    try:
        return json.loads(raw)
    except Exception:
        print("⚠️ Failed to parse LLM JSON response")
        return {}
