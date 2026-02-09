from __future__ import annotations

import sys
from pathlib import Path

from .parser import parse
from .compiler import compile_program
from .runtime import run


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "run":
        print("Usage: aidsl run <file.ai>")
        print()
        print("Example: uv run python -m aidsl run examples/expense.ai")
        print()
        print("Requires GITHUB_TOKEN env var (GitHub PAT with models:read)")
        sys.exit(1)

    filepath = sys.argv[2]

    if not Path(filepath).exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    print(f"\n  PARSE   {filepath}")
    program = parse(filepath)

    print(f"  COMPILE {program.extract_target} -> {len(program.flags)} flag rules")
    plan = compile_program(program)

    print(f"  RUN     {plan.source} -> {plan.output}\n")
    run(plan, base_dir=str(Path(filepath).parent))


if __name__ == "__main__":
    main()
