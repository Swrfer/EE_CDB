"""Descarga ESummary para los PMID obtenidos con ESearch."""

import json
from pathlib import Path

from clientes.adapters import (
    require_list,
    require_object,
    require_string,
)
from clientes.base import RobustAPIClient
from clientes.fetch import fetch_json_and_store
from clientes.raw_storage import (
    RawParameter,
    RawResponseStore,
)

ESUMMARY_URL = (
    "https://eutils.ncbi.nlm.nih.gov"
    "/entrez/eutils/esummary.fcgi"
)


def latest_pubmed_search(
    raw_root: Path,
) -> Path:
    """Localiza el cuerpo ESearch más reciente."""
    candidates = [
        path
        for path in (raw_root / "pubmed").glob("*.json")
        if not path.name.endswith(".metadata.json")
    ]

    if not candidates:
        raise FileNotFoundError(
            "No se encontró un ESearch crudo de PubMed."
        )

    return max(
        candidates,
        key=lambda path: path.stat().st_mtime_ns,
    )


def extract_pmids(search_path: Path) -> list[str]:
    """Extrae PMID del ESearch guardado."""
    payload: object = json.loads(
        search_path.read_text(encoding="utf-8")
    )

    root = require_object(
        payload,
        "PubMed ESearch",
    )

    search_result = require_object(
        root.get("esearchresult"),
        "esearchresult",
    )

    id_values = require_list(
        search_result.get("idlist"),
        "idlist",
    )

    pmids = [
        require_string(
            value,
            f"idlist[{index}]",
        )
        for index, value in enumerate(id_values)
    ]

    if not pmids:
        raise ValueError(
            "ESearch no contiene PMID."
        )

    return pmids


def main() -> None:
    """Descarga y conserva el resumen bibliográfico."""
    project_root = Path(__file__).resolve().parents[1]
    raw_root = project_root / "data" / "raw"

    search_path = latest_pubmed_search(
        raw_root
    )
    pmids = extract_pmids(search_path)

    params: dict[str, RawParameter] = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
        "tool": "biomedical_api_lab08",
    }

    store = RawResponseStore(
        root=raw_root,
    )

    client = RobustAPIClient(
        cache_name=(
            project_root
            / ".cache"
            / "activity06_pubmed"
        ),
        user_agent="biomedical-api-client/0.1 lab08",
    )

    with client:
        result = fetch_json_and_store(
            client=client,
            store=store,
            source="pubmed_summary",
            url=ESUMMARY_URL,
            params=params,
        )

    print("===== PUBMED ESUMMARY =====")
    print("PMID solicitados:", pmids)
    print(
        "Cuerpo:",
        result.artifact.body_path.relative_to(
            project_root
        ),
    )
    print(
        "Metadatos:",
        result.artifact.metadata_path.relative_to(
            project_root
        ),
    )
    print(
        "Bytes:",
        result.artifact.body_path.stat().st_size,
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
