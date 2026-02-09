from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path

import httpx

from .compiler import ExecutionPlan

# GitHub Models inference endpoint (OpenAI chat completions compatible)
_GITHUB_MODELS_URL = "https://models.github.ai/inference/chat/completions"
_DEFAULT_MODEL = "openai/gpt-4.1-mini"


def run(plan: ExecutionPlan, base_dir: str = ".") -> list[dict]:
    token = os.environ.get("GITHUB_TOKEN", "")
    model = os.environ.get("AIDSL_MODEL", _DEFAULT_MODEL)
    if not token:
        print("  ERROR: Set GITHUB_TOKEN env var (GitHub PAT with models:read)")
        sys.exit(1)

    source_path = Path(base_dir) / plan.source
    if not source_path.exists():
        print(f"  ERROR: Source file not found: {source_path}")
        sys.exit(1)

    with open(source_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"  READ {len(rows)} rows from {plan.source}")
    print(f"  SCHEMA: {plan.schema.name} ({len(plan.schema.fields)} fields)")
    print(f"  FLAGS: {len(plan.flag_evaluator.rules)} rules")
    print(f"  MODEL: {model}\n")

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
            print("           FAILED")
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
                        time.sleep(2 ** attempt)
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
