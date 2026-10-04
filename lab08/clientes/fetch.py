"""Frontera entre la descarga cruda y la transformación JSON."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from clientes.base import RobustAPIClient
from clientes.raw_storage import (
    RawArtifact,
    RawParameter,
    RawResponseStore,
)


@dataclass(frozen=True, slots=True)
class FetchedJSON:
    """JSON validado como objeto y archivos crudos asociados."""

    payload: dict[str, Any]
    artifact: RawArtifact


def fetch_json_and_store(
    *,
    client: RobustAPIClient,
    store: RawResponseStore,
    source: str,
    url: str,
    params: dict[str, RawParameter] | None = None,
) -> FetchedJSON:
    """Descarga, guarda los bytes y solo después interpreta JSON."""
    response = client.request(
        "GET",
        url,
        params=params,
    )

    artifact = store.save(
        source=source,
        response=response,
        params=params,
    )

    payload: object = response.json()

    if not isinstance(payload, dict):
        raise TypeError(
            "La API no devolvió un objeto JSON."
        )

    return FetchedJSON(
        payload=payload,
        artifact=artifact,
    )
