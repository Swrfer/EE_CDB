"""Descarga una respuesta cruda de cada API biomédica."""

from dataclasses import dataclass
from pathlib import Path

from clientes.base import RobustAPIClient
from clientes.fetch import fetch_json_and_store
from clientes.raw_storage import (
    RawParameter,
    RawResponseStore,
)


@dataclass(frozen=True, slots=True)
class SourceQuery:
    """Configuración reproducible de una consulta."""

    source: str
    url: str
    params: dict[str, RawParameter]


QUERIES = (
    SourceQuery(
        source="pubmed",
        url=(
            "https://eutils.ncbi.nlm.nih.gov"
            "/entrez/eutils/esearch.fcgi"
        ),
        params={
            "db": "pubmed",
            "term": (
                '("stomach neoplasms"[MeSH Terms] '
                'OR "gastric cancer"[Title/Abstract])'
            ),
            "retmode": "json",
            "retmax": 3,
            "tool": "biomedical_api_lab08",
        },
    ),
    SourceQuery(
        source="clinicaltrials",
        url="https://clinicaltrials.gov/api/v2/studies",
        params={
            "query.cond": "gastric cancer",
            "pageSize": 3,
            "countTotal": "true",
            "format": "json",
        },
    ),
    SourceQuery(
        source="openfda",
        url="https://api.fda.gov/drug/event.json",
        params={
            "search": (
                'patient.drug.drugindication:'
                '"GASTRIC CANCER"'
            ),
            "limit": 3,
        },
    ),
)


def main() -> None:
    """Guarda los bytes antes de inspeccionar el JSON."""
    project_root = Path(__file__).resolve().parents[1]

    store = RawResponseStore(
        root=project_root / "data" / "raw",
    )

    client = RobustAPIClient(
        cache_name=(
            project_root
            / ".cache"
            / "activity05"
        ),
        user_agent="biomedical-api-client/0.1 lab08",
    )

    with client:
        for query in QUERIES:
            result = fetch_json_and_store(
                client=client,
                store=store,
                source=query.source,
                url=query.url,
                params=query.params,
            )

            body_path = result.artifact.body_path
            metadata_path = result.artifact.metadata_path

            print(f"===== {query.source.upper()} =====")
            print(
                "Cuerpo:",
                body_path.relative_to(project_root),
            )
            print(
                "Metadatos:",
                metadata_path.relative_to(project_root),
            )
            print(
                "Bytes:",
                body_path.stat().st_size,
            )
            print(
                "Claves JSON:",
                sorted(result.payload),
            )

    print("===== MÉTRICAS =====")
    print(
        "Peticiones reales:",
        client.metrics.real_requests,
    )
    print(
        "Respuestas desde caché:",
        client.metrics.cache_hits,
    )
    print(
        "Reintentos:",
        client.metrics.retries,
    )


if __name__ == "__main__":
    main()
