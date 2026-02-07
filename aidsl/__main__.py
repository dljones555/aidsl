from __future__ import annotations

import sys
from pathlib import Path

from .parser import parse
from .compiler import compile_program
from .runtime import run


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "run":
        print("Usage: aidsl run <file.ai> [--mock]")
        print()
        print("  --mock   Run with regex extraction (no API key needed)")
        print()
        print("Example: uv run python -m aidsl run examples/expense.ai --mock")
        sys.exit(1)

    filepath = sys.argv[2]
    mock = "--mock" in sys.argv

    if not Path(filepath).exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    print(f"\n  PARSE   {filepath}")
    program = parse(filepath)

    print(f"  COMPILE {program.extract_target} -> {len(program.flags)} flag rules")
    plan = compile_program(program)

    print(f"  RUN     {plan.source} -> {plan.output}\n")
    run(plan, base_dir=str(Path(filepath).parent), mock=mock)


if __name__ == "__main__":
    main()
