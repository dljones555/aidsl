"""Agent runner: parse pipeline.ai, run extraction, split results."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aidsl.parser import parse
from aidsl.compiler import compile_program
from aidsl.runtime import run

HERE = Path(__file__).resolve().parent
TIMESTAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

# Parse, compile, run
program = parse(str(HERE / "pipeline.ai"))
plan = compile_program(program, base_dir=str(HERE))
results = run(plan, base_dir=str(HERE))

# Split results
errors = [r for r in results if "_error" in r]
flagged = [r for r in results if r.get("_flagged")]
clean = [r for r in results if not r.get("_flagged") and "_error" not in r]

# Write to output folders
for category, records in [("clean", clean), ("flagged", flagged), ("errors", errors)]:
    if records:
        out = HERE / "output" / category / f"run_{TIMESTAMP}.json"
        out.write_text(json.dumps(records, indent=2), encoding="utf-8")

# Append audit log
audit_entry = {
    "timestamp": TIMESTAMP,
    "inbox_files": len(results),
    "clean": len(clean),
    "flagged": len(flagged),
    "errors": len(errors),
}
audit_path = HERE / "output" / "audit" / "log.jsonl"
with open(audit_path, "a", encoding="utf-8") as f:
    f.write(json.dumps(audit_entry) + "\n")

print(f"\n  AGENT RUN {TIMESTAMP}")
print(f"  clean={len(clean)}  flagged={len(flagged)}  errors={len(errors)}")
print("  audit -> output/audit/log.jsonl")
