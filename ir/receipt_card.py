"""Verify receipt card: the user-presentable artifact of a run.

A RunReceipt is the machine record — digests, flags, verdicts. The card
is what a non-technical stakeholder reads: what ran, what each step did,
what the model said, what the human decided, and what it cost.

Deterministic: same receipt, same card — no timestamps, no randomness.
Stdlib only.

The receipt carries output *digests*, not values. The card shows values
only when the host passes them in (``outputs`` maps step var -> value);
the host holds the values during the run, the receipt stays the
tamper-evident record.
"""

from __future__ import annotations

import json
from typing import Any

from .executor import RunReceipt, StepReceipt

_MAX_VALUE_CHARS = 400


def render_card(
    receipt: RunReceipt, outputs: dict[str, Any] | None = None
) -> str:
    """Render a RunReceipt as a Markdown verify-receipt card.

    Args:
        receipt: The run record from the executor.
        outputs: Optional mapping of step var -> actual output value,
            shown for external (model) steps. When absent, the card
            shows the output digest instead.

    Returns:
        The card as Markdown text, ending in a single newline.
    """
    shown = outputs or {}
    lines = [
        f"# Verify receipt — {receipt.plan}",
        "",
        _spec_line(receipt),
        "",
        "## What ran",
        "",
        *[_step_line(s) for s in receipt.steps],
        "",
        "## What the model said",
        "",
        *_model_lines(receipt, shown),
        "",
        "## What the human decided",
        "",
        *_human_lines(receipt),
        "",
        "## Cost",
        "",
        _cost_line(receipt),
        "",
        "_Provenance: step inputs/outputs are recorded as digests in the "
        "run receipt — the tamper-evident trail._",
    ]
    return "\n".join(lines).rstrip("\n") + "\n"


def _spec_line(receipt: RunReceipt) -> str:
    """One-line run identity: spec, version, status."""
    return (
        f"**Spec:** {receipt.spec} {receipt.version} · "
        f"**Status:** {receipt.status}"
    )


def _outcome(step: StepReceipt) -> str:
    """Plain-words outcome for one step receipt."""
    if step.skipped:
        return "skipped"
    if step.suspended:
        return "suspended — awaiting human verdict"
    if step.dropped:
        return f"dropped by gate verdict {step.verdict!r}"
    if step.shadow_blocked:
        return "approved but blocked by deny list (shadow mode)"
    return "completed"


def _step_line(step: StepReceipt) -> str:
    """One card line per step: what it did and how it landed."""
    line = f"- {step.var} = {step.op} ({step.effect}) — {_outcome(step)}"
    tokens = step.tokens_in + step.tokens_out
    if tokens:
        line += f" ({tokens} tokens)"
    if step.gate:
        line += f" [gate {step.gate}]"
    if step.flags:
        line += f" — flagged: {', '.join(step.flags)}"
    return line


def _model_lines(
    receipt: RunReceipt, outputs: dict[str, Any]
) -> list[str]:
    """What the model said: external-step outputs, values or digests."""
    lines = []
    for s in receipt.steps:
        if s.effect != "external" or s.skipped:
            continue
        if s.var in outputs:
            lines.append(f"- {s.var}: {_fmt_value(outputs[s.var])}")
        else:
            lines.append(
                f"- {s.var}: output digest `{s.outputs_digest}` "
                "(value not supplied)"
            )
    return lines or ["- No external (model) steps ran."]


def _human_lines(receipt: RunReceipt) -> list[str]:
    """What the human decided: gate verdicts, or gates still waiting."""
    lines = []
    for s in receipt.steps:
        if s.verdict:
            lines.append(f"- {s.gate or 'gate'}: {s.verdict}")
        elif s.suspended:
            lines.append(f"- {s.gate or 'gate'}: awaiting verdict")
    return lines or ["- No human decisions."]


def _cost_line(receipt: RunReceipt) -> str:
    """Cost from the record: tokens, human minutes, audit failures."""
    parts = [
        f"tokens used: {receipt.tokens_used}",
        f"human minutes: {receipt.human_minutes_used}",
    ]
    if receipt.audit_failures:
        parts.append(f"audit failures: {', '.join(receipt.audit_failures)}")
    else:
        parts.append("audit failures: none")
    return "- " + " · ".join(parts)


def _fmt_value(value: Any) -> str:
    """Compact JSON rendering of an output value, truncated for the card."""
    text = json.dumps(value, sort_keys=True, default=str)
    if len(text) > _MAX_VALUE_CHARS:
        text = text[:_MAX_VALUE_CHARS] + "…"
    return f"`{text}`"
