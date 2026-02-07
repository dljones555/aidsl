from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path

import httpx

from .compiler import ExecutionPlan

# GitHub Models inference endpoint (OpenAI chat completions compatible)
_GITHUB_MODELS_URL = "https://models.github.ai/inference/chat/completions"
_DEFAULT_MODEL = "openai/gpt-4.1-mini"


def run(plan: ExecutionPlan, base_dir: str = ".", mock: bool = False) -> list[dict]:
    source_path = Path(base_dir) / plan.source
    if not source_path.exists():
        print(f"  ERROR: Source file not found: {source_path}")
        sys.exit(1)

    with open(source_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"  READ {len(rows)} rows from {plan.source}")
    print(f"  SCHEMA: {plan.schema.name} ({len(plan.schema.fields)} fields)")
    print(f"  FLAGS: {len(plan.flag_evaluator.rules)} rules")

    if mock:
        print(f"  MODE: mock (regex extraction, no LLM)\n")
        extractor = _extract_mock
    else:
        token = os.environ.get("GITHUB_TOKEN", "")
        model = os.environ.get("AIDSL_MODEL", _DEFAULT_MODEL)
        if not token:
            print("  ERROR: Set GITHUB_TOKEN env var (GitHub PAT with models:read)")
            print("         Or use --mock to run without an API key")
            sys.exit(1)
        print(f"  MODE: llm ({model})\n")
        extractor = _make_llm_extractor(token, model)

    results = []

    for i, row in enumerate(rows):
        text = row.get("text", "")
        if not text:
            continue
        print(f"  [{i + 1}/{len(rows)}] EXTRACT: {text[:55]}...")

        record = extractor(plan, text)

        if record:
            # Deterministic flag evaluation — no LLM needed
            flags = plan.flag_evaluator.evaluate(record)
            record["_flagged"] = len(flags) > 0
            record["_flag_reasons"] = flags
            record["_source"] = text

            status = "FLAGGED" if flags else "OK"
            flag_info = f" ({', '.join(flags)})" if flags else ""
            print(f"           {status}{flag_info}")

            results.append(record)
        else:
            print(f"           FAILED")
            results.append({"_source": text, "_error": "extraction failed"})

    # Write output
    output_path = Path(base_dir) / plan.output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n  OUTPUT {len(results)} records -> {plan.output}")
    flagged = sum(1 for r in results if r.get("_flagged"))
    clean = sum(1 for r in results if r.get("_flagged") is False)
    errors = sum(1 for r in results if "_error" in r)
    print(f"  SUMMARY: {clean} clean | {flagged} flagged | {errors} errors")

    return results


# ---------------------------------------------------------------------------
# Mock extractor — regex-based, no API key needed, proves the full pipeline
# ---------------------------------------------------------------------------

# Keywords that map to schema categories
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "travel": ["uber", "lyft", "taxi", "flight", "delta", "united", "airline", "hotel", "marriott", "hilton", "airbnb"],
    "meals": ["lunch", "dinner", "breakfast", "chipotle", "starbucks", "coffee", "restaurant", "food", "pastries"],
    "equipment": ["macbook", "laptop", "monitor", "apple store", "keyboard", "mouse", "ipad", "phone"],
    "software": ["github", "subscription", "license", "saas", "slack", "notion", "jira"],
    "office": ["staples", "paper", "toner", "office depot", "supplies", "pens"],
}


def _extract_mock(plan: ExecutionPlan, text: str) -> dict | None:
    record: dict = {}
    text_lower = text.lower()

    for f in plan.schema.fields:
        if f.type == "TEXT":
            # Extract merchant: first recognizable proper noun / brand
            record[f.name] = _guess_merchant(text)
        elif f.type == "MONEY":
            # Extract dollar amount
            match = re.search(r"\$\s*([\d,]+\.?\d+)", text)
            if match:
                record[f.name] = float(match.group(1).replace(",", ""))
            else:
                match = re.search(r"([\d,]+\.\d{2})", text)
                record[f.name] = float(match.group(1).replace(",", "")) if match else 0.0
        elif f.type == "ENUM":
            # Match against enum values using keyword lists
            record[f.name] = _match_category(text_lower, f.enum_values)
        elif f.type == "BOOL":
            record[f.name] = False
        elif f.type == "NUMBER":
            match = re.search(r"(\d+\.?\d*)", text)
            record[f.name] = float(match.group(1)) if match else 0

    # Validate enum constraints
    if not _validate(record, plan):
        return None

    return record


def _guess_merchant(text: str) -> str:
    brands = [
        "Uber", "Lyft", "Chipotle", "Apple Store", "GitHub", "Marriott",
        "Staples", "Delta", "Starbucks", "Amazon", "Office Depot", "Hilton",
    ]
    text_lower = text.lower()
    for brand in brands:
        if brand.lower() in text_lower:
            return brand
    # Fallback: first capitalized word
    match = re.search(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)", text)
    return match.group(1) if match else "Unknown"


def _match_category(text_lower: str, allowed: list[str]) -> str:
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if category in allowed:
            for kw in keywords:
                if kw in text_lower:
                    return category
    return allowed[0] if allowed else "other"


# ---------------------------------------------------------------------------
# LLM extractor — GitHub Models inference API (OpenAI compatible)
# ---------------------------------------------------------------------------

def _make_llm_extractor(token: str, model: str):
    client = httpx.Client(timeout=30.0)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }

    def _extract_llm(plan: ExecutionPlan, text: str, retries: int = 2) -> dict | None:
        for attempt in range(retries + 1):
            try:
                body = {
                    "model": model,
                    "max_tokens": 256,
                    "messages": [
                        {"role": "system", "content": plan.extraction_prompt.system},
                        {"role": "user", "content": text},
                    ],
                }
                resp = client.post(_GITHUB_MODELS_URL, headers=headers, json=body)

                if resp.status_code != 200:
                    print(f"           HTTP {resp.status_code}: {resp.text[:120]}")
                    if attempt < retries:
                        import time
                        time.sleep(2 ** attempt)  # backoff: 1s, 2s
                        continue
                    return None

                data = resp.json()
                raw = data["choices"][0]["message"]["content"].strip()

                # Strip markdown code fences if present
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1]
                    raw = raw.rsplit("```", 1)[0].strip()

                record = json.loads(raw)

                if _validate(record, plan):
                    return record

                if attempt < retries:
                    print(f"           retry ({attempt + 1}) - validation failed")

            except Exception as e:
                if attempt < retries:
                    print(f"           retry ({attempt + 1}) - {e}")

        return None

    return _extract_llm


def _validate(record: dict, plan: ExecutionPlan) -> bool:
    props = plan.extraction_prompt.json_schema.get("properties", {})

    for name, schema in props.items():
        if name not in record:
            return False

        value = record[name]

        if schema.get("type") == "number":
            try:
                record[name] = float(value) if not isinstance(value, (int, float)) else value
            except (ValueError, TypeError):
                return False

        if "enum" in schema:
            if value not in schema["enum"]:
                return False

    return True
