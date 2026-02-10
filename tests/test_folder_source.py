from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from aidsl.parser import parse
from aidsl.compiler import compile_program
from aidsl.runtime import _load_source


# --- _load_source unit tests ---


def test_load_source_csv(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text('text\n"hello world"\n"second row"\n')
    rows = _load_source(csv_file)
    assert len(rows) == 2
    assert rows[0]["text"] == "hello world"


def test_load_source_folder(tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "a.txt").write_text("First document content")
    (folder / "b.txt").write_text("Second document content")
    rows = _load_source(folder)
    assert len(rows) == 2
    assert rows[0]["text"] == "First document content"
    assert rows[0]["_filename"] == "a.txt"
    assert rows[1]["_filename"] == "b.txt"


def test_load_source_folder_sorted(tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "c.txt").write_text("Third")
    (folder / "a.txt").write_text("First")
    (folder / "b.txt").write_text("Second")
    rows = _load_source(folder)
    assert [r["_filename"] for r in rows] == ["a.txt", "b.txt", "c.txt"]


def test_load_source_folder_mixed_extensions(tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "invoice.txt").write_text("A text invoice")
    (folder / "receipt.email").write_text("An email receipt")
    (folder / "report.ocr").write_text("OCR output")
    rows = _load_source(folder)
    assert len(rows) == 3
    filenames = [r["_filename"] for r in rows]
    assert "invoice.txt" in filenames
    assert "receipt.email" in filenames
    assert "report.ocr" in filenames


def test_load_source_folder_skips_hidden(tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "visible.txt").write_text("I should be loaded")
    (folder / ".hidden").write_text("I should be skipped")
    rows = _load_source(folder)
    assert len(rows) == 1
    assert rows[0]["_filename"] == "visible.txt"


def test_load_source_folder_skips_empty_files(tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "has_content.txt").write_text("Real content here")
    (folder / "empty.txt").write_text("")
    (folder / "whitespace.txt").write_text("   \n  \n  ")
    rows = _load_source(folder)
    assert len(rows) == 1
    assert rows[0]["_filename"] == "has_content.txt"


def test_load_source_empty_folder(tmp_path):
    folder = tmp_path / "empty"
    folder.mkdir()
    rows = _load_source(folder)
    assert rows == []


# --- Parser: FROM folder path ---


def test_parse_from_folder(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  name TEXT\n\nFROM docs/\nEXTRACT x\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.source == "docs/"


def test_parse_from_folder_no_trailing_slash(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text("DEFINE x:\n  name TEXT\n\nFROM mydir\nEXTRACT x\nOUTPUT o.json\n")
    prog = parse(str(ai))
    assert prog.source == "mydir"


# --- Full pipeline with folder source (mocked LLM) ---


def test_runtime_folder_source_pipeline(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  name TEXT\n\n"
        "FROM docs/\nEXTRACT x\nFLAG WHEN name IS danger\nOUTPUT o.json\n"
    )

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "file1.txt").write_text("John Smith is a consultant")
    (docs / "file2.txt").write_text("Jane danger zone")

    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))

    resp1 = MagicMock()
    resp1.status_code = 200
    resp1.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"name": "John Smith"})}}]
    }

    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"name": "danger"})}}]
    }

    import os
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post.side_effect = [resp1, resp2]
            mock_client_cls.return_value = mock_client

            from aidsl.runtime import run
            results = run(plan, base_dir=str(tmp_path))

    assert len(results) == 2
    assert results[0]["name"] == "John Smith"
    assert results[0]["_flagged"] is False
    assert results[1]["name"] == "danger"
    assert results[1]["_flagged"] is True
