"""Model inference API — the seam where nondeterminism enters.

Every EXTERNAL op calls a ModelClient. The IR never names a vendor:
the binding supplies the client. Three implementations ship in v0.1:

  CannedModel  — scripted responses, for tests. Zero cost, deterministic.
  FileModel    — SUPER-MUSE mode: reads responses from a JSONL file, one
                 object per line:
                   {"op": "<op>", "data": {...}, "tokens_in": n, "tokens_out": m}
                 A human (or a very handsome assistant) plays the model by
                 writing the file. complete() raises NeedModelResponse when
                 no entry matches, carrying the prompt so the human knows
                 what to answer. This is the $0 demo path: the executor is
                 real, the determinism is real, and the only nondeterminism
                 in the building is me.
  GateIO       — how gates get verdicts: AutoVerdict for tests/demos,
                 SuspendAlways to watch a run stop at a human gate.

Swap FileModel for a DBOS-wrapped durable call or a Claude Managed
Agents session later. The spec does not change — that is the point.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .model import Gate


@dataclass
class ModelResult:
    data: dict[str, Any]
    tokens_in: int = 0
    tokens_out: int = 0


class ModelClient(Protocol):
    def complete(
        self, *, op: str, prompt: str, schema: dict[str, Any]
    ) -> ModelResult: ...


class NeedModelResponse(Exception):
    """Raised by FileModel when super-muse hasn't answered yet."""

    def __init__(self, op: str, prompt: str):
        super().__init__(f"super-muse, please answer for op '{op}'")
        self.op = op
        self.prompt = prompt


class CannedModel:
    """Scripted model for tests. responses[op_name] -> dict | ModelResult,
    or a list of those consumed in order (for fanned-out steps)."""

    def __init__(self, responses: dict[str, Any]):
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def complete(self, *, op: str, prompt: str, schema: dict[str, Any]) -> ModelResult:
        self.calls.append({"op": op, "prompt": prompt})
        if op not in self.responses:
            raise KeyError(f"no canned response for op '{op}'")
        r = self.responses[op]
        if isinstance(r, list):
            if not r:
                raise KeyError(f"canned responses for op '{op}' exhausted")
            r = r.pop(0)
        if isinstance(r, ModelResult):
            return r
        return ModelResult(data=r, tokens_in=10, tokens_out=20)


class FileModel:
    """Super-muse mode: the human plays the model via a JSONL file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.calls: list[dict[str, Any]] = []

    def _entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text().splitlines()
            if line.strip()
        ]

    def complete(self, *, op: str, prompt: str, schema: dict[str, Any]) -> ModelResult:
        self.calls.append({"op": op, "prompt": prompt})
        entries = self._entries()
        for entry in entries:
            if entry.get("op") == op and not entry.get("consumed"):
                entry["consumed"] = True
                self.path.write_text(
                    "\n".join(json.dumps(e) for e in entries) + "\n"
                )
                return ModelResult(
                    data=entry["data"],
                    tokens_in=int(entry.get("tokens_in", 0)),
                    tokens_out=int(entry.get("tokens_out", 0)),
                )
        raise NeedModelResponse(op, prompt)


class GateIO(Protocol):
    def ask_verdict(self, gate: Gate, item: Any) -> str | None:
        """Return a verdict from gate.verdicts, or None to leave it suspended."""
        ...


@dataclass
class AutoVerdict:
    verdict: str

    def ask_verdict(self, gate: Gate, item: Any) -> str | None:
        if self.verdict not in gate.verdicts:
            raise ValueError(
                f"verdict {self.verdict!r} not in gate '{gate.name}' "
                f"vocabulary {gate.verdicts}"
            )
        return self.verdict


@dataclass
class SuspendAlways:
    seen: list[dict[str, Any]] = field(default_factory=list)

    def ask_verdict(self, gate: Gate, item: Any) -> str | None:
        self.seen.append({"gate": gate.name, "item": item})
        return None
