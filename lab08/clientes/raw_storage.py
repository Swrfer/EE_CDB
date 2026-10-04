"""Almacenamiento reproducible de respuestas HTTP crudas."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

from requests import Response

RawParameter = str | int | float | bool | None
ClockFunction = Callable[[], datetime]

SENSITIVE_PARAMETERS = frozenset(
    {
        "api_key",
        "apikey",
        "access_token",
        "token",
        "key",
    }
)


@dataclass(frozen=True, slots=True)
class RawArtifact:
    """Rutas del cuerpo crudo y sus metadatos."""

    body_path: Path
    metadata_path: Path


class RawResponseStore:
    """Guarda respuestas exactas antes de transformarlas."""

    def __init__(
        self,
        root: str | Path = "data/raw",
        *,
        clock: ClockFunction | None = None,
    ) -> None:
        self.root = Path(root)
        self.clock = clock
        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        *,
        source: str,
        response: Response,
        params: dict[str, RawParameter] | None = None,
    ) -> RawArtifact:
        """Guarda el cuerpo exacto y un archivo lateral reproducible."""
        safe_source = self._safe_source(source)
        downloaded_at = self._utc_now()
        body = response.content
        digest = hashlib.sha256(body).hexdigest()

        extension = self._extension_from_content_type(
            response.headers.get("Content-Type", "")
        )

        timestamp = downloaded_at.strftime(
            "%Y%m%dT%H%M%S%fZ"
        )

        source_directory = self.root / safe_source
        source_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            f"{safe_source}_{timestamp}_{digest[:12]}"
            f"{extension}"
        )

        body_path = source_directory / filename
        metadata_path = source_directory / (
            f"{body_path.stem}.metadata.json"
        )

        body_path.write_bytes(body)

        request_method = None

        if response.request is not None:
            request_method = response.request.method

        metadata: dict[str, object] = {
            "schema_version": 1,
            "source": safe_source,
            "downloaded_at_utc": downloaded_at.isoformat(),
            "method": request_method,
            "status_code": response.status_code,
            "requested_url": self._redact_url(response.url),
            "parameters": self._redact_params(
                params or {}
            ),
            "content_type": response.headers.get(
                "Content-Type"
            ),
            "content_length_bytes": len(body),
            "body_sha256": digest,
            "from_cache": bool(
                getattr(response, "from_cache", False)
            ),
            "response_headers": dict(response.headers),
        }

        metadata_path.write_text(
            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        return RawArtifact(
            body_path=body_path,
            metadata_path=metadata_path,
        )

    def _utc_now(self) -> datetime:
        """Obtiene una fecha consciente y normalizada a UTC."""
        current = (
            self.clock()
            if self.clock is not None
            else datetime.now(UTC)
        )

        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)

        return current.astimezone(UTC)

    @staticmethod
    def _safe_source(source: str) -> str:
        """Convierte el nombre de la fuente en una ruta segura."""
        cleaned = re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            source.strip(),
        ).strip("_")

        if not cleaned:
            raise ValueError(
                "source debe contener al menos un carácter válido."
            )

        return cleaned.lower()

    @staticmethod
    def _extension_from_content_type(
        content_type: str,
    ) -> str:
        """Selecciona una extensión sin transformar el contenido."""
        normalized = content_type.lower()

        if "json" in normalized:
            return ".json"

        if "xml" in normalized:
            return ".xml"

        return ".bin"

    @staticmethod
    def _redact_params(
        params: dict[str, RawParameter],
    ) -> dict[str, RawParameter | str]:
        """Oculta credenciales en los parámetros documentados."""
        return {
            key: (
                "***REDACTED***"
                if key.lower() in SENSITIVE_PARAMETERS
                else value
            )
            for key, value in params.items()
        }

    @staticmethod
    def _redact_url(url: str) -> str:
        """Oculta credenciales incluidas en la URL final."""
        parts = urlsplit(url)
        query_pairs = parse_qsl(
            parts.query,
            keep_blank_values=True,
        )

        redacted_pairs = [
            (
                key,
                (
                    "***REDACTED***"
                    if key.lower() in SENSITIVE_PARAMETERS
                    else value
                ),
            )
            for key, value in query_pairs
        ]

        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(redacted_pairs),
                parts.fragment,
            )
        )
