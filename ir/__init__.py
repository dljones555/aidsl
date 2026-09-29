"""Work Surface IR — Layer 2. See ir/model.py for the contract."""

from __future__ import annotations

from .check import Violation, check
from .eval import evaluate, parse_ok
from .exec import Executor, RunReceipt, StepReceipt
from .lower import lower_program
from .model import (
    AuditRule,
    Effect,
    Field,
    Gate,
    Knowledge,
    Op,
    Plan,
    PlanStep,
    Spec,
    TypeDef,
    dumps,
    loads,
)
from .stub import (
    AutoVerdict,
    CannedModel,
    FileModel,
    GateIO,
    ModelClient,
    ModelResult,
    NeedModelResponse,
    SuspendAlways,
)

__all__ = [
    "AuditRule",
    "AutoVerdict",
    "CannedModel",
    "Effect",
    "Executor",
    "Field",
    "FileModel",
    "Gate",
    "GateIO",
    "Knowledge",
    "ModelClient",
    "ModelResult",
    "NeedModelResponse",
    "Op",
    "Plan",
    "PlanStep",
    "RunReceipt",
    "Spec",
    "StepReceipt",
    "SuspendAlways",
    "TypeDef",
    "Violation",
    "check",
    "dumps",
    "evaluate",
    "loads",
    "lower_program",
    "parse_ok",
]
