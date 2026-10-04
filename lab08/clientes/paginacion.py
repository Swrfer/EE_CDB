"""Paginación incremental de ClinicalTrials.gov."""

from collections.abc import Iterator
from typing import Any, cast

import requests
from requests import Session

from clientes.clinical_trials import DEFAULT_TIMEOUT, STUDIES_URL


def iterar_estudios(
    condicion: str,
    *,
    page_size: int = 100,
    max_records: int | None = None,
    session: Session | None = None,
) -> Iterator[dict[str, Any]]:
    """Entrega estudios uno a uno sin acumularlos en una lista.

    Parameters
    ----------
    condicion
        Condición clínica enviada como ``query.cond``.
    page_size
        Número máximo de estudios solicitado en cada página.
    max_records
        Límite total de estudios entregados. ``None`` recorre todas las páginas.
    session
        Sesión opcional que puede reutilizar conexiones o incorporar caché.
    """
    if not condicion.strip():
        raise ValueError("La condición no puede estar vacía.")

    if not 1 <= page_size <= 1000:
        raise ValueError("page_size debe estar entre 1 y 1000.")

    if max_records is not None and max_records < 1:
        raise ValueError("max_records debe ser positivo o None.")

    owns_session = session is None
    http = session if session is not None else requests.Session()

    page_token: str | None = None
    seen_tokens: set[str] = set()
    yielded = 0

    try:
        while True:
            params: dict[str, str | int] = {
                "query.cond": condicion,
                "pageSize": page_size,
                "format": "json",
            }

            if page_token is not None:
                params["pageToken"] = page_token

            response = http.get(
                STUDIES_URL,
                params=params,
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()

            payload: object = response.json()

            if not isinstance(payload, dict):
                raise TypeError(
                    "ClinicalTrials.gov no devolvió un objeto JSON."
                )

            studies: object = payload.get("studies", [])

            if not isinstance(studies, list):
                raise TypeError(
                    "El campo studies no contiene una lista."
                )

            for study in studies:
                if not isinstance(study, dict):
                    raise TypeError(
                        "Se recibió un estudio con formato inválido."
                    )

                yielded += 1
                yield cast(dict[str, Any], study)

                if (
                    max_records is not None
                    and yielded >= max_records
                ):
                    return

            next_token: object = payload.get("nextPageToken")

            if next_token is None:
                return

            if not isinstance(next_token, str) or not next_token:
                raise TypeError(
                    "nextPageToken tiene un formato inválido."
                )

            if next_token in seen_tokens:
                raise RuntimeError(
                    "ClinicalTrials.gov repitió un pageToken."
                )

            seen_tokens.add(next_token)
            page_token = next_token
    finally:
        if owns_session:
            http.close()
