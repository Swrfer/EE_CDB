"""Pruebas de la frontera entre descarga y transformación."""

from pathlib import Path

import pytest
import requests
import responses

from clientes.base import RobustAPIClient
from clientes.fetch import fetch_json_and_store
from clientes.raw_storage import RawResponseStore

TEST_URL = "https://example.test/invalid-json"


@responses.activate
def test_raw_response_is_saved_before_json_parsing(
    tmp_path: Path,
) -> None:
    """Los bytes sobreviven aunque el parseo posterior falle."""
    invalid_json = b"<html>temporary error</html>\n"

    responses.add(
        responses.GET,
        TEST_URL,
        body=invalid_json,
        status=200,
        content_type="application/json",
    )

    store = RawResponseStore(
        root=tmp_path / "raw",
    )

    client = RobustAPIClient(
        cache_name="fetch_test",
        cache_backend="memory",
        sleep_func=lambda _: None,
    )

    with (
        client,
        pytest.raises(
            requests.exceptions.JSONDecodeError
        ),
    ):
        fetch_json_and_store(
            client=client,
            store=store,
            source="test_source",
            url=TEST_URL,
            params={"query": "gastric cancer"},
        )

    source_directory = (
        tmp_path
        / "raw"
        / "test_source"
    )

    saved_bodies = [
        path
        for path in source_directory.glob("*.json")
        if not path.name.endswith(".metadata.json")
    ]

    metadata_files = list(
        source_directory.glob("*.metadata.json")
    )

    assert len(saved_bodies) == 1
    assert len(metadata_files) == 1
    assert saved_bodies[0].read_bytes() == invalid_json
    assert client.metrics.real_requests == 1
    assert len(responses.calls) == 1
