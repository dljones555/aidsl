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
        print(f"  ERROR: Source not found: {source_path}")
        sys.exit(1)

    rows = _load_source(source_path)

    print(f"  READ {len(rows)} rows from {plan.source}")
    print(f"  SCHEMA: {plan.schema.name} ({len(plan.schema.fields)} fields)")
    print(f"  FLAGS: {len(plan.flag_evaluator.rules)} rules")
    print(f"  MODEL: {model}\n")

    client = httpx.Client(timeout=30.0)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }
    extractor = _make_llm_extractor(client, headers, model)
    results = []

    for i, row in enumerate(rows):
        text = row.get("text", "")
        if not text:
            continue
        print(f"  [{i + 1}/{len(rows)}] EXTRACT: {text[:55]}...")

        record = extractor(plan, text)

        if record:
            # DRAFT step — second LLM call if configured
            if plan.draft_prompt:
                draft_text, resolved_prompt = _draft_llm(client, headers, model, plan, record)
                if draft_text:
                    record[plan.draft_prompt.field_name] = draft_text
                    record["_draft_prompt"] = resolved_prompt
                    print(f"           PROMPT: {resolved_prompt[:70]}...")
                    print(f"           DRAFT: {draft_text[:60]}...")

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
# Source loading — CSV files or folders of text files
# ---------------------------------------------------------------------------

def _load_source(source_path: Path) -> list[dict]:
    """Load input rows from a CSV file or a folder of files.

    CSV: standard DictReader, expects a 'text' column.
    Folder: reads all files (skipping hidden/dot files), each file becomes
            a row with 'text' = file contents, '_filename' = file name.
    """
    if source_path.is_dir():
        rows = []
        for f in sorted(source_path.iterdir()):
            if f.is_file() and not f.name.startswith("."):
                text = f.read_text(encoding="utf-8").strip()
                if text:
                    rows.append({"text": text, "_filename": f.name})
        return rows

    with open(source_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# LLM extractor — GitHub Models inference API (OpenAI compatible)
# ---------------------------------------------------------------------------

def _make_llm_extractor(client: httpx.Client, headers: dict, model: str):
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


def _substitute_placeholders(template: str, record: dict) -> str:
    """Replace {field_name} placeholders with values from the record.

    Uses simple string replacement — not Jinja/Handlebars.
    Unknown placeholders are left as-is.
    """
    result = template
    for key, value in record.items():
        if not key.startswith("_"):
            result = result.replace("{" + key + "}", str(value))
    return result


def _draft_llm(
    client: httpx.Client, headers: dict, model: str,
    plan: ExecutionPlan, record: dict,
) -> tuple[str | None, str]:
    """Second LLM call: generate text from structured record.

    Returns (draft_text, resolved_prompt) — the resolved prompt shows
    the template after {field} substitution for audit/debugging.
    """
    draft = plan.draft_prompt

    # Substitute {field} placeholders in the system prompt from the record
    system_prompt = _substitute_placeholders(draft.system, record)

    user_msg = json.dumps(record, indent=2)

    body = {
        "model": model,
        "max_tokens": 512,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
    }
    try:
        resp = client.post(_GITHUB_MODELS_URL, headers=headers, json=body)
        if resp.status_code != 200:
            return None, system_prompt
        data = resp.json()
        raw = data["choices"][0]["message"]["content"].strip()

        # Try to parse as JSON and extract the field
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0].strip()
        try:
            parsed = json.loads(raw)
            return str(parsed.get(draft.field_name, raw)), system_prompt
        except json.JSONDecodeError:
            # LLM returned plain text — use as-is
            return raw, system_prompt
    except Exception:
        return None, system_prompt


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
