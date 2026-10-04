"""Pruebas del almacenamiento de respuestas crudas."""

import json
from datetime import UTC, datetime
from pathlib import Path

from requests import Request, Response

from clientes.raw_storage import RawResponseStore

FIXED_TIME = datetime(
    2026,
    10,
    4,
    17,
    30,
    0,
    tzinfo=UTC,
)


def make_response(
    *,
    body: bytes,
    url: str,
    content_type: str,
) -> Response:
    """Construye una respuesta local sin tocar la red."""
    request = Request(
        method="GET",
        url=url,
    ).prepare()

    response = Response()
    response.status_code = 200
    response._content = body
    response.headers["Content-Type"] = content_type
    response.headers["X-Test-Header"] = "preserved"
    response.request = request
    response.url = request.url or url

    return response


def test_raw_body_is_preserved_and_metadata_is_written(
    tmp_path: Path,
) -> None:
    """El cuerpo se conserva byte por byte y la llave se censura."""
    original_body = (
        b'{ "term" : "c\xc3\xa1ncer", '
        b'"items" : [3, 2, 1] }\n'
    )

    response = make_response(
        body=original_body,
        url=(
            "https://example.test/api"
            "?api_key=secret-value"
            "&search=gastric+cancer"
        ),
        content_type="application/json; charset=utf-8",
    )

    store = RawResponseStore(
        root=tmp_path / "raw",
        clock=lambda: FIXED_TIME,
    )

    artifact = store.save(
        source="Open FDA",
        response=response,
        params={
            "api_key": "secret-value",
            "search": "gastric cancer",
            "limit": 3,
        },
    )

    assert artifact.body_path.read_bytes() == original_body
    assert artifact.body_path.suffix == ".json"
    assert artifact.body_path.parent.name == "open_fda"
    assert artifact.metadata_path.exists()

    metadata_text = artifact.metadata_path.read_text(
        encoding="utf-8"
    )

    assert "secret-value" not in metadata_text
    assert "***REDACTED***" in metadata_text

    metadata: object = json.loads(metadata_text)

    assert isinstance(metadata, dict)
    assert metadata["schema_version"] == 1
    assert metadata["source"] == "open_fda"
    assert metadata["status_code"] == 200
    assert metadata["downloaded_at_utc"] == (
        "2026-10-04T17:30:00+00:00"
    )
    assert metadata["content_length_bytes"] == len(
        original_body
    )
    assert metadata["from_cache"] is False
    assert metadata["parameters"] == {
        "api_key": "***REDACTED***",
        "limit": 3,
        "search": "gastric cancer",
    }
    assert metadata["response_headers"][
        "X-Test-Header"
    ] == "preserved"


def test_non_json_body_is_saved_without_parsing(
    tmp_path: Path,
) -> None:
    """El almacén acepta bytes aunque no formen JSON válido."""
    original_body = b"<not-json>\xff\x00"

    response = make_response(
        body=original_body,
        url="https://example.test/raw",
        content_type="application/octet-stream",
    )

    store = RawResponseStore(
        root=tmp_path / "raw",
        clock=lambda: FIXED_TIME,
    )

    artifact = store.save(
        source="unknown",
        response=response,
    )

    assert artifact.body_path.suffix == ".bin"
    assert artifact.body_path.read_bytes() == original_body
