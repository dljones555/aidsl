from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .parser import Condition, DraftDef, FieldDef, FlagRule, Program, Schema, Settings


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
class DraftPrompt:
    system: str  # prompt template (may contain {field} placeholders)
    field_name: str  # output field name for the generated text


@dataclass
class ExecutionPlan:
    source: str
    extraction_prompt: ExtractionPrompt
    flag_evaluator: FlagEvaluator
    output: str
    schema: Schema
    verb: str = "EXTRACT"  # EXTRACT or CLASSIFY
    draft_prompt: DraftPrompt | None = None
    settings: Settings = None  # type: ignore[assignment]


def compile_program(program: Program, base_dir: str = ".") -> ExecutionPlan:
    if program.classify:
        plan = _compile_classify(program, base_dir)
    else:
        plan = _compile_extract(program, base_dir)

    if program.draft:
        plan.draft_prompt = _compile_draft(program.draft, base_dir)

    plan.settings = program.settings

    return plan


def _load_prompt_file(name: str, base_dir: str) -> str:
    """Load a .prompt file from prompts/ folder relative to base_dir."""
    prompt_path = Path(base_dir) / "prompts" / f"{name}.prompt"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}\n"
            f"  Create prompts/{name}.prompt alongside your .ai file"
        )
    return prompt_path.read_text(encoding="utf-8").strip()


def _load_examples_file(name: str, base_dir: str) -> list[tuple[str, str]]:
    """Load a .examples file from examples/ folder relative to base_dir.

    Format:
        INPUT: some text here
        OUTPUT: {"field": "value"}

        INPUT: another example
        OUTPUT: {"field": "other"}

    Returns list of (input, output) string pairs.
    """
    examples_path = Path(base_dir) / "examples" / f"{name}.examples"
    if not examples_path.exists():
        raise FileNotFoundError(
            f"Examples file not found: {examples_path}\n"
            f"  Create examples/{name}.examples alongside your .ai file"
        )
    text = examples_path.read_text(encoding="utf-8").strip()
    pairs: list[tuple[str, str]] = []
    current_input = ""
    current_output = ""

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("INPUT:"):
            # Save previous pair if we have one
            if current_input and current_output:
                pairs.append((current_input.strip(), current_output.strip()))
            current_input = line[6:].strip()
            current_output = ""
        elif line.startswith("OUTPUT:"):
            current_output = line[7:].strip()

    # Don't forget the last pair
    if current_input and current_output:
        pairs.append((current_input.strip(), current_output.strip()))

    return pairs


def _format_examples(pairs: list[tuple[str, str]]) -> str:
    """Format example pairs into prompt text for few-shot learning."""
    lines = ["Here are some examples:", ""]
    for i, (inp, out) in enumerate(pairs, 1):
        lines.append(f"Example {i}:")
        lines.append(f"  Input: {inp}")
        lines.append(f"  Output: {out}")
        lines.append("")
    lines.append("Now process the following input the same way.")
    return "\n".join(lines)


def _field_to_json_schema(f: FieldDef, all_schemas: dict[str, Schema]) -> dict:
    """Convert a FieldDef to a JSON schema fragment, resolving nested types."""
    if f.type == "TEXT":
        return {"type": "string"}
    elif f.type == "MONEY":
        return {"type": "number"}
    elif f.type == "NUMBER":
        return {"type": "number"}
    elif f.type == "BOOL":
        return {"type": "boolean"}
    elif f.type == "ENUM":
        return {"type": "string", "enum": f.enum_values}
    elif f.type == "LIST":
        ref_schema = all_schemas.get(f.ref_type)
        if not ref_schema:
            raise ValueError(f"Referenced type '{f.ref_type}' not defined")
        item_props, item_required = _schema_to_json(ref_schema, all_schemas)
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": item_props,
                "required": item_required,
            },
        }
    elif f.type == "REF":
        ref_schema = all_schemas.get(f.ref_type)
        if not ref_schema:
            raise ValueError(f"Referenced type '{f.ref_type}' not defined")
        ref_props, ref_required = _schema_to_json(ref_schema, all_schemas)
        return {
            "type": "object",
            "properties": ref_props,
            "required": ref_required,
        }
    return {"type": "string"}


def _schema_to_json(
    schema: Schema, all_schemas: dict[str, Schema]
) -> tuple[dict, list[str]]:
    """Convert a Schema's fields to JSON schema properties + required list."""
    props: dict = {}
    required: list[str] = []
    for f in schema.fields:
        required.append(f.name)
        props[f.name] = _field_to_json_schema(f, all_schemas)
    return props, required


def _field_to_prompt_desc(f: FieldDef, all_schemas: dict[str, Schema]) -> str:
    """Generate a human-readable prompt description for a field."""
    if f.type == "TEXT":
        return f"- {f.name}: text string"
    elif f.type == "MONEY":
        return f"- {f.name}: numeric dollar amount (number only, no $ sign)"
    elif f.type == "NUMBER":
        return f"- {f.name}: numeric value"
    elif f.type == "BOOL":
        return f"- {f.name}: true or false"
    elif f.type == "ENUM":
        values_str = ", ".join(f.enum_values)
        return f"- {f.name}: MUST be exactly one of: {values_str}"
    elif f.type == "LIST":
        ref_schema = all_schemas.get(f.ref_type)
        if ref_schema:
            sub_fields = ", ".join(sf.name for sf in ref_schema.fields)
            return f"- {f.name}: array of {f.ref_type} objects, each with: {sub_fields}"
        return f"- {f.name}: array of {f.ref_type} objects"
    elif f.type == "REF":
        ref_schema = all_schemas.get(f.ref_type)
        if ref_schema:
            sub_fields = ", ".join(sf.name for sf in ref_schema.fields)
            return f"- {f.name}: {f.ref_type} object with: {sub_fields}"
        return f"- {f.name}: {f.ref_type} object"
    return f"- {f.name}: text string"


def _compile_extract(program: Program, base_dir: str) -> ExecutionPlan:
    schema = program.schemas.get(program.extract_target)
    if not schema:
        raise ValueError(f"Schema '{program.extract_target}' not defined")

    prompt_lines: list[str] = []

    # Prepend WITH context if provided
    if program.prompt_name:
        context = _load_prompt_file(program.prompt_name, base_dir)
        prompt_lines.append(context)
        prompt_lines.append("")

    prompt_lines.extend(
        [
            "Extract the following fields from the input text.",
            "Return a JSON object with EXACTLY these fields:\n",
        ]
    )

    json_properties, required = _schema_to_json(schema, program.schemas)

    for f in schema.fields:
        prompt_lines.append(_field_to_prompt_desc(f, program.schemas))

    # Append few-shot examples if USE provided
    if program.examples_name:
        pairs = _load_examples_file(program.examples_name, base_dir)
        if pairs:
            prompt_lines.append("")
            prompt_lines.append(_format_examples(pairs))

    prompt_lines.append(
        "\nReturn ONLY a valid JSON object. No markdown, no explanation."
    )

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
        verb="EXTRACT",
    )


def _compile_classify(program: Program, base_dir: str) -> ExecutionPlan:
    classify = program.classify
    values_str = ", ".join(classify.categories)

    prompt_lines: list[str] = []

    # Prepend WITH context if provided
    if program.prompt_name:
        context = _load_prompt_file(program.prompt_name, base_dir)
        prompt_lines.append(context)
        prompt_lines.append("")

    prompt_lines.extend(
        [
            "Classify the input text into exactly one category.",
            f"Categories: {values_str}",
            "",
            f'Return a JSON object with one field "{classify.field_name}" '
            f"whose value is exactly one of: {values_str}",
        ]
    )

    # Append few-shot examples if USE provided
    if program.examples_name:
        pairs = _load_examples_file(program.examples_name, base_dir)
        if pairs:
            prompt_lines.append("")
            prompt_lines.append(_format_examples(pairs))

    prompt_lines.extend(
        [
            "",
            "Return ONLY a valid JSON object. No markdown, no explanation.",
        ]
    )

    json_schema = {
        "type": "object",
        "properties": {
            classify.field_name: {
                "type": "string",
                "enum": classify.categories,
            }
        },
        "required": [classify.field_name],
    }

    # Build a synthetic schema so the rest of the pipeline works
    schema = Schema(
        name="_classify",
        fields=[FieldDef(classify.field_name, "ENUM", classify.categories)],
    )

    return ExecutionPlan(
        source=program.source,
        extraction_prompt=ExtractionPrompt(
            system="\n".join(prompt_lines),
            json_schema=json_schema,
        ),
        flag_evaluator=FlagEvaluator(rules=program.flags),
        output=program.output,
        schema=schema,
        verb="CLASSIFY",
    )


def _compile_draft(draft: DraftDef, base_dir: str) -> DraftPrompt:
    prompt_lines: list[str] = []

    if draft.prompt_name:
        template = _load_prompt_file(draft.prompt_name, base_dir)
        prompt_lines.append(template)
        prompt_lines.append("")

    prompt_lines.extend(
        [
            "Given the structured data below, generate the requested text.",
            f'Put your response in the "{draft.field_name}" field.',
            "",
            "Return ONLY a valid JSON object with one field. No markdown, no explanation.",
        ]
    )

    # Add few-shot examples if USE provided
    if draft.examples_name:
        pairs = _load_examples_file(draft.examples_name, base_dir)
        if pairs:
            prompt_lines.append("")
            prompt_lines.append(_format_examples(pairs))

    return DraftPrompt(
        system="\n".join(prompt_lines),
        field_name=draft.field_name,
    )
