from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

from .compiler import compile_program
from .parser import (
    ClassifyDef,
    DraftDef,
    FieldDef,
    FlagRule,
    Program,
    Schema,
    Settings,
    _parse_flag_rule,
)
from .runtime import (
    _DEFAULT_MODEL,
    _draft_llm,
    _make_llm_extractor,
    _row_to_text,
    run,
)


class SchemaBuilder:
    """Fluent builder for Schema / FieldDef dataclasses."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._fields: list[FieldDef] = []
        self._deps: dict[str, Schema] = {}

    # -- field helpers (each returns self for chaining) --

    def text(self, name: str) -> SchemaBuilder:
        self._fields.append(FieldDef(name, "TEXT"))
        return self

    def money(self, name: str) -> SchemaBuilder:
        self._fields.append(FieldDef(name, "MONEY"))
        return self

    def number(self, name: str) -> SchemaBuilder:
        self._fields.append(FieldDef(name, "NUMBER"))
        return self

    def bool(self, name: str) -> SchemaBuilder:
        self._fields.append(FieldDef(name, "BOOL"))
        return self

    def enum(self, name: str, values: list[str]) -> SchemaBuilder:
        self._fields.append(FieldDef(name, "ENUM", enum_values=values))
        return self

    def list_of(self, name: str, schema: Schema) -> SchemaBuilder:
        self._fields.append(FieldDef(name, "LIST", ref_type=schema.name))
        self._deps[schema.name] = schema
        # Propagate transitive deps
        if hasattr(schema, "_deps"):
            self._deps.update(schema._deps)
        return self

    def ref(self, name: str, schema: Schema) -> SchemaBuilder:
        self._fields.append(FieldDef(name, "REF", ref_type=schema.name))
        self._deps[schema.name] = schema
        if hasattr(schema, "_deps"):
            self._deps.update(schema._deps)
        return self

    def build(self) -> Schema:
        schema = Schema(name=self._name, fields=list(self._fields))
        # Stash deps on the schema object so Pipeline can collect them
        schema._deps = dict(self._deps)  # type: ignore[attr-defined]
        return schema

    @classmethod
    def from_json(cls, source: str | dict) -> Schema:
        """Build a Schema from a JSON file path or a dict.

        Expected format::

            {"name": "claim", "fields": {"claimant": "text", "amount": "money"}}

        Supported type strings: text, money, number, bool.
        For enums, use a list: ``{"category": ["auto", "property", "health"]}``.
        """
        if isinstance(source, (str, Path)):
            with open(source) as f:
                spec = json.load(f)
        else:
            spec = source

        _type_map = {
            "text": "TEXT",
            "money": "MONEY",
            "number": "NUMBER",
            "bool": "BOOL",
        }

        builder = cls(spec["name"])
        for field_name, field_type in spec["fields"].items():
            if isinstance(field_type, list):
                builder.enum(field_name, field_type)
            else:
                mapped = _type_map.get(field_type.lower())
                if mapped is None:
                    raise ValueError(
                        f"Unknown type '{field_type}' for field '{field_name}'"
                    )
                builder._fields.append(FieldDef(field_name, mapped))
        return builder.build()


class Pipeline:
    """Fluent builder for Program; calls compile_program() + run()."""

    def __init__(self) -> None:
        self._source: str = ""
        self._output: str = ""
        self._extract_schema: Schema | None = None
        self._classify_def: ClassifyDef | None = None
        self._draft_def: DraftDef | None = None
        self._prompt_name: str = ""
        self._examples_name: str = ""
        self._flags: list[FlagRule] = []
        self._settings = Settings()
        self._base_dir: str = "."

    # -- builder methods (each returns self) --

    def source(self, path: str) -> Pipeline:
        self._source = path
        return self

    def extract(self, schema: Schema) -> Pipeline:
        if self._classify_def is not None:
            raise ValueError("extract() and classify() are mutually exclusive")
        self._extract_schema = schema
        return self

    def classify(self, field_name: str, categories: list[str]) -> Pipeline:
        if self._extract_schema is not None:
            raise ValueError("extract() and classify() are mutually exclusive")
        self._classify_def = ClassifyDef(field_name=field_name, categories=categories)
        return self

    def draft(self, field_name: str) -> Pipeline:
        self._draft_def = DraftDef(field_name=field_name)
        return self

    def prompt(self, name: str) -> Pipeline:
        self._prompt_name = name
        return self

    def examples(self, name: str) -> Pipeline:
        self._examples_name = name
        return self

    def flag(self, rule_str: str) -> Pipeline:
        self._flags.append(_parse_flag_rule(rule_str))
        return self

    def set(self, **kwargs: object) -> Pipeline:
        if "model" in kwargs:
            self._settings.model = str(kwargs["model"])
        if "temperature" in kwargs:
            self._settings.temperature = float(kwargs["temperature"])  # type: ignore[arg-type]
        if "top_p" in kwargs:
            self._settings.top_p = float(kwargs["top_p"])  # type: ignore[arg-type]
        if "seed" in kwargs:
            self._settings.seed = int(kwargs["seed"])  # type: ignore[arg-type]
        if "headers" in kwargs:
            self._settings.headers = kwargs["headers"]  # type: ignore[assignment]
        return self

    def output(self, path: str) -> Pipeline:
        self._output = path
        return self

    def base_dir(self, path: str) -> Pipeline:
        self._base_dir = path
        return self

    # -- terminal methods --

    def to_program(self) -> Program:
        """Build and return the raw Program AST."""
        schemas: dict[str, Schema] = {}

        if self._extract_schema is not None:
            schemas[self._extract_schema.name] = self._extract_schema
            # Collect nested deps
            if hasattr(self._extract_schema, "_deps"):
                schemas.update(self._extract_schema._deps)  # type: ignore[attr-defined]

        return Program(
            schemas=schemas,
            source=self._source,
            extract_target=(self._extract_schema.name if self._extract_schema else ""),
            classify=self._classify_def,
            draft=self._draft_def,
            prompt_name=self._prompt_name,
            examples_name=self._examples_name,
            flags=list(self._flags),
            output=self._output or "output.json",
            settings=self._settings,
        )

    def run(self) -> list[dict]:
        """Compile and run the full batch pipeline (requires source + output)."""
        if not self._source:
            raise ValueError("source() is required before run()")
        program = self.to_program()
        plan = compile_program(program, base_dir=self._base_dir)
        return run(plan, base_dir=self._base_dir)

    def run_one(self, text: str) -> dict:
        """Process a single record without file I/O."""
        program = self.to_program()
        plan = compile_program(program, base_dir=self._base_dir)
        return _run_single(plan, text)


def _run_single(plan, text: str) -> dict:
    """Process one record through the pipeline without file I/O."""
    token = os.environ.get("GITHUB_TOKEN", "")
    model = plan.settings.model or os.environ.get("AIDSL_MODEL", _DEFAULT_MODEL)

    client = httpx.Client(timeout=30.0)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }

    extractor = _make_llm_extractor(client, headers, model)

    # Convert text to row dict for _row_to_text compatibility
    try:
        row = json.loads(text)
        if not isinstance(row, dict):
            row = {"text": text}
    except (json.JSONDecodeError, ValueError):
        row = {"text": text}

    input_text = _row_to_text(row)
    record = extractor(plan, input_text)

    if record is None:
        return {"_error": "extraction failed", "_source": text}

    # DRAFT step
    if plan.draft_prompt:
        draft_text, resolved_prompt = _draft_llm(client, headers, model, plan, record)
        if draft_text:
            record[plan.draft_prompt.field_name] = draft_text
            record["_draft_prompt"] = resolved_prompt

    # Deterministic flag evaluation
    flags = plan.flag_evaluator.evaluate(record)
    record["_flagged"] = len(flags) > 0
    record["_flag_reasons"] = flags
    record["_source"] = text

    return record
