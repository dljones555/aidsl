from __future__ import annotations

import json

from aidsl.runtime import _load_source


def test_load_json_file_array(tmp_path):
    json_file = tmp_path / "data.json"
    data = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]
    json_file.write_text(json.dumps(data))
    rows = _load_source(json_file)
    assert len(rows) == 2
    assert rows[0]["name"] == "Alice"
    assert rows[1]["name"] == "Bob"


def test_load_json_file_single_object(tmp_path):
    json_file = tmp_path / "data.json"
    data = {"name": "Charlie", "age": 35}
    json_file.write_text(json.dumps(data))
    rows = _load_source(json_file)
    assert len(rows) == 1
    assert rows[0]["name"] == "Charlie"


def test_load_json_file_empty_array(tmp_path):
    json_file = tmp_path / "data.json"
    json_file.write_text("[]")
    rows = _load_source(json_file)
    assert rows == []


def test_load_folder_with_json_files(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()

    # Single object per file
    (folder / "item1.json").write_text(json.dumps({"id": 1, "value": "A"}))
    (folder / "item2.json").write_text(json.dumps({"id": 2, "value": "B"}))

    rows = _load_source(folder)
    assert len(rows) == 2
    assert rows[0]["id"] == 1
    assert rows[1]["id"] == 2


def test_load_folder_with_json_array_file(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()

    # Array in one file
    batch = [
        {"id": 1, "value": "A"},
        {"id": 2, "value": "B"},
        {"id": 3, "value": "C"},
    ]
    (folder / "batch.json").write_text(json.dumps(batch))

    rows = _load_source(folder)
    assert len(rows) == 3
    assert rows[0]["id"] == 1
    assert rows[2]["id"] == 3


def test_load_folder_mixed_json_and_text(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()

    (folder / "item.json").write_text(json.dumps({"type": "structured"}))
    (folder / "note.txt").write_text("Unstructured text content")

    rows = _load_source(folder)
    assert len(rows) == 2
    # JSON file parsed as dict
    assert rows[0]["type"] == "structured"
    # Text file kept as text blob
    assert rows[1]["text"] == "Unstructured text content"


def test_load_folder_multiple_json_files_mixed(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()

    # Single object
    (folder / "a.json").write_text(json.dumps({"id": 1}))
    # Array
    (folder / "b.json").write_text(json.dumps([{"id": 2}, {"id": 3}]))
    # Another single object
    (folder / "c.json").write_text(json.dumps({"id": 4}))

    rows = _load_source(folder)
    assert len(rows) == 4
    assert [r["id"] for r in rows] == [1, 2, 3, 4]
