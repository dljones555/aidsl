from __future__ import annotations

from dataclasses import dataclass, field

from .parser import Program, Schema, FlagRule, Condition


@dataclass
class ExtractionPrompt:
    system: str
    json_schema: dict


@dataclass
class FlagEvaluator:
    rules: list[FlagRule]

    def evaluate(self, record: dict) -> list[str]:
        reasons = []
        for rule in self.rules:
            if self._eval_rule(rule, record):
                reasons.append(self._describe(rule))
        return reasons

    def _eval_rule(self, rule: FlagRule, record: dict) -> bool:
        if not rule.conditions:
            return False
        results = [self._eval_cond(c, record) for c in rule.conditions]
        result = results[0]
        for i, conj in enumerate(rule.conjunctions):
            if i + 1 < len(results):
                if conj == "AND":
                    result = result and results[i + 1]
                else:
                    result = result or results[i + 1]
        return result

    def _eval_cond(self, cond: Condition, record: dict) -> bool:
        value = record.get(cond.field)
        if value is None:
            return False
        if cond.op == "OVER":
            try:
                return float(value) > float(cond.value)
            except (ValueError, TypeError):
                return False
        elif cond.op == "UNDER":
            try:
                return float(value) < float(cond.value)
            except (ValueError, TypeError):
                return False
        elif cond.op == "IS":
            return str(value).lower() == cond.value.lower()
        return False

    def _describe(self, rule: FlagRule) -> str:
        parts = []
        for i, cond in enumerate(rule.conditions):
            parts.append(f"{cond.field} {cond.op} {cond.value}")
            if i < len(rule.conjunctions):
                parts.append(rule.conjunctions[i])
        return " ".join(parts)


@dataclass
class ExecutionPlan:
    source: str
    extraction_prompt: ExtractionPrompt
    flag_evaluator: FlagEvaluator
    output: str
    schema: Schema


def compile_program(program: Program) -> ExecutionPlan:
    schema = program.schemas.get(program.extract_target)
    if not schema:
        raise ValueError(f"Schema '{program.extract_target}' not defined")

    # Build constrained extraction prompt from schema
    prompt_lines = [
        "Extract the following fields from the input text.",
        "Return a JSON object with EXACTLY these fields:\n",
    ]

    json_properties: dict = {}
    required: list[str] = []

    for f in schema.fields:
        required.append(f.name)
        if f.type == "TEXT":
            prompt_lines.append(f"- {f.name}: text string")
            json_properties[f.name] = {"type": "string"}
        elif f.type == "MONEY":
            prompt_lines.append(f"- {f.name}: numeric dollar amount (number only, no $ sign)")
            json_properties[f.name] = {"type": "number"}
        elif f.type == "NUMBER":
            prompt_lines.append(f"- {f.name}: numeric value")
            json_properties[f.name] = {"type": "number"}
        elif f.type == "BOOL":
            prompt_lines.append(f"- {f.name}: true or false")
            json_properties[f.name] = {"type": "boolean"}
        elif f.type == "ENUM":
            values_str = ", ".join(f.enum_values)
            prompt_lines.append(f"- {f.name}: MUST be exactly one of: {values_str}")
            json_properties[f.name] = {"type": "string", "enum": f.enum_values}

    prompt_lines.append("\nReturn ONLY a valid JSON object. No markdown, no explanation.")

    json_schema = {
        "type": "object",
        "properties": json_properties,
        "required": required,
    }

    return ExecutionPlan(
        source=program.source,
        extraction_prompt=ExtractionPrompt(
            system="\n".join(prompt_lines),
            json_schema=json_schema,
        ),
        flag_evaluator=FlagEvaluator(rules=program.flags),
        output=program.output,
        schema=schema,
    )
