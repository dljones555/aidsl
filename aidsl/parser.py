from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class FieldDef:
    name: str
    type: str  # TEXT, MONEY, NUMBER, BOOL, ENUM
    enum_values: list[str] = field(default_factory=list)


@dataclass
class Schema:
    name: str
    fields: list[FieldDef] = field(default_factory=list)


@dataclass
class Condition:
    field: str
    op: str  # OVER, UNDER, IS
    value: str


@dataclass
class FlagRule:
    conditions: list[Condition] = field(default_factory=list)
    conjunctions: list[str] = field(default_factory=list)


@dataclass
class ClassifyDef:
    field_name: str  # output field name for the classification result
    categories: list[str] = field(default_factory=list)


@dataclass
class DraftDef:
    field_name: str  # output field name for the generated text
    prompt_name: str = ""  # WITH <name> — .prompt template
    examples_name: str = ""  # USE <name> — .examples file


@dataclass
class Program:
    schemas: dict[str, Schema] = field(default_factory=dict)
    source: str = ""
    extract_target: str = ""
    classify: ClassifyDef | None = None
    draft: DraftDef | None = None
    prompt_name: str = ""  # WITH <name> — references a .prompt file
    examples_name: str = ""  # USE <name> — references a .examples file
    flags: list[FlagRule] = field(default_factory=list)
    output: str = ""


def parse(filepath: str) -> Program:
    with open(filepath) as f:
        lines = f.readlines()

    program = Program()
    current_schema: Schema | None = None
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped or stripped.startswith("--"):
            i += 1
            continue

        # DEFINE block
        if stripped.startswith("DEFINE "):
            match = re.match(r"DEFINE\s+(\w+)\s*:", stripped)
            if match:
                name = match.group(1)
                current_schema = Schema(name=name)
                program.schemas[name] = current_schema
            i += 1
            continue

        # Field definition (indented, inside DEFINE block)
        if current_schema and line[0] in (" ", "\t"):
            parts = stripped.split(None, 1)
            if len(parts) == 2:
                field_name, type_str = parts
                if type_str == "TEXT":
                    current_schema.fields.append(FieldDef(field_name, "TEXT"))
                elif type_str == "MONEY":
                    current_schema.fields.append(FieldDef(field_name, "MONEY"))
                elif type_str == "NUMBER":
                    current_schema.fields.append(FieldDef(field_name, "NUMBER"))
                elif type_str == "YES/NO":
                    current_schema.fields.append(FieldDef(field_name, "BOOL"))
                elif type_str.startswith("ONE OF"):
                    enum_match = re.search(r"\[([^\]]+)\]", type_str)
                    if enum_match:
                        values = [v.strip() for v in enum_match.group(1).split(",")]
                        current_schema.fields.append(FieldDef(field_name, "ENUM", values))
            i += 1
            continue

        # Non-indented line ends any schema block
        current_schema = None

        if stripped.startswith("FROM "):
            program.source = stripped[5:].strip()
        elif stripped.startswith("EXTRACT "):
            target, with_name, use_name = _split_modifiers(stripped[8:])
            program.extract_target = target
            if with_name:
                program.prompt_name = with_name
            if use_name:
                program.examples_name = use_name
        elif stripped.startswith("CLASSIFY "):
            program.classify = _parse_classify(stripped)
            # Check for WITH and USE on the CLASSIFY line
            with_match = re.search(r"\bWITH\s+(\w+)", stripped)
            if with_match:
                program.prompt_name = with_match.group(1)
            use_match = re.search(r"\bUSE\s+(\w+)", stripped)
            if use_match:
                program.examples_name = use_match.group(1)
        elif stripped.startswith("DRAFT "):
            target, with_name, use_name = _split_modifiers(stripped[6:])
            program.draft = DraftDef(
                field_name=target,
                prompt_name=with_name,
                examples_name=use_name,
            )
        elif stripped.startswith("WITH "):
            rest = stripped[5:].strip()
            # Handle "WITH ctx USE ex" on one line
            use_in_with = re.search(r"\bUSE\s+(\w+)", rest)
            if use_in_with:
                program.examples_name = use_in_with.group(1)
                program.prompt_name = rest[:use_in_with.start()].strip()
            else:
                program.prompt_name = rest
        elif stripped.startswith("USE "):
            rest = stripped[4:].strip()
            # Handle "USE ex WITH ctx" on one line
            with_in_use = re.search(r"\bWITH\s+(\w+)", rest)
            if with_in_use:
                program.prompt_name = with_in_use.group(1)
                program.examples_name = rest[:with_in_use.start()].strip()
            else:
                program.examples_name = rest
        elif stripped.startswith("FLAG WHEN "):
            program.flags.append(_parse_flag_rule(stripped[10:]))
        elif stripped.startswith("OUTPUT "):
            program.output = stripped[7:].strip()

        i += 1

    return program


def _split_modifiers(text: str) -> tuple[str, str, str]:
    """Split 'expense WITH ctx USE ex' into ('expense', 'ctx', 'ex').

    Supports WITH and USE in any order on the same line.
    Returns (target, with_name, use_name).
    """
    text = text.strip()

    with_name = ""
    use_name = ""

    with_match = re.search(r"\bWITH\s+(\w+)", text)
    if with_match:
        with_name = with_match.group(1)

    use_match = re.search(r"\bUSE\s+(\w+)", text)
    if use_match:
        use_name = use_match.group(1)

    # Target is the first word before any modifier keyword
    target_match = re.match(r"(\w+)", text)
    target = target_match.group(1) if target_match else text

    return target, with_name, use_name


def _parse_classify(text: str) -> ClassifyDef:
    # CLASSIFY INTO [a, b, c]
    # CLASSIFY <field_name> INTO [a, b, c]
    enum_match = re.search(r"\[([^\]]+)\]", text)
    categories = []
    if enum_match:
        categories = [v.strip() for v in enum_match.group(1).split(",")]

    # Check for optional field name: CLASSIFY type INTO [...]
    into_match = re.match(r"CLASSIFY\s+(\w+)\s+INTO\s+", text)
    if into_match and into_match.group(1) != "INTO":
        field_name = into_match.group(1)
    else:
        field_name = "classification"

    return ClassifyDef(field_name=field_name, categories=categories)


def _parse_flag_rule(text: str) -> FlagRule:
    tokens = re.split(r"\s+(AND|OR)\s+", text)
    conditions: list[Condition] = []
    conjunctions: list[str] = []

    for token in tokens:
        token = token.strip()
        if token in ("AND", "OR"):
            conjunctions.append(token)
            continue

        match = re.match(r"(\w+)\s+(OVER|UNDER|IS)\s+(.+)", token)
        if match:
            conditions.append(Condition(match.group(1), match.group(2), match.group(3).strip()))

    return FlagRule(conditions=conditions, conjunctions=conjunctions)
