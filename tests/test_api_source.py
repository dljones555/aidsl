from __future__ import annotations

from unittest.mock import MagicMock, patch

from aidsl.runtime import _load_source
from aidsl.parser import parse
from aidsl.compiler import compile_program


def test_load_api_source_array(tmp_path):
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": 1, "status": "open"},
            {"id": 2, "status": "closed"},
        ]
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        rows = _load_source(tmp_path, source_str="https://api.example.com/tickets")
        assert len(rows) == 2
        assert rows[0]["id"] == 1
        assert rows[1]["status"] == "closed"


def test_load_api_source_single_object(tmp_path):
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 1, "status": "open"}
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        rows = _load_source(tmp_path, source_str="https://api.example.com/ticket/1")
        assert len(rows) == 1
        assert rows[0]["id"] == 1


def test_load_api_source_with_headers(tmp_path):
    headers = {"Authorization": "Bearer token123", "X-Custom": "value"}
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"data": "test"}]
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        rows = _load_source(
            tmp_path, source_str="https://api.example.com/data", headers=headers
        )

        # Verify headers were passed
        mock_client.get.assert_called_once_with(
            "https://api.example.com/data", headers=headers
        )
        assert len(rows) == 1


def test_parse_set_header(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  a TEXT\n\n"
        "SET HEADER Authorization Bearer abc123\n"
        "FROM https://api.example.com/tickets\n"
        "EXTRACT x\nOUTPUT o.json\n"
    )
    prog = parse(str(ai))
    assert prog.settings.headers["Authorization"] == "Bearer abc123"


def test_parse_multiple_headers(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  a TEXT\n\n"
        "SET HEADER Authorization Bearer xyz\n"
        "SET HEADER X-API-Key secret123\n"
        "FROM https://api.example.com/tickets\n"
        "EXTRACT x\nOUTPUT o.json\n"
    )
    prog = parse(str(ai))
    assert prog.settings.headers["Authorization"] == "Bearer xyz"
    assert prog.settings.headers["X-API-Key"] == "secret123"


def test_compile_headers_passthrough(tmp_path):
    ai = tmp_path / "t.ai"
    ai.write_text(
        "DEFINE x:\n  a TEXT\n\n"
        "SET HEADER Authorization Bearer token\n"
        "FROM https://api.example.com/data\n"
        "EXTRACT x\nOUTPUT o.json\n"
    )
    prog = parse(str(ai))
    plan = compile_program(prog, base_dir=str(tmp_path))
    assert plan.settings.headers["Authorization"] == "Bearer token"
