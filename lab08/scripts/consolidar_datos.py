"""Normaliza los registros validados y genera archivos Parquet."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pandas as pd

type JSONObject = dict[str, object]


ACTIVE_TRIAL_STATUSES = {
    "ACTIVE_NOT_RECRUITING",
    "ENROLLING_BY_INVITATION",
    "NOT_YET_RECRUITING",
    "RECRUITING",
}


def load_json_object(path: Path) -> JSONObject:
    """Carga un archivo JSON cuya raíz debe ser un objeto."""
    payload = cast(
        object,
        json.loads(
            path.read_text(
                encoding="utf-8",
            )
        ),
    )

    if not isinstance(payload, dict):
        raise TypeError(
            f"{path} no contiene un objeto JSON.",
        )

    return cast(JSONObject, payload)


def require_object(
    container: JSONObject,
    key: str,
) -> JSONObject:
    """Obtiene un objeto JSON obligatorio."""
    value = container.get(key)

    if not isinstance(value, dict):
        raise TypeError(
            f"{key} debe ser un objeto JSON.",
        )

    return cast(JSONObject, value)


def require_records(
    container: JSONObject,
    key: str,
) -> list[JSONObject]:
    """Obtiene una lista obligatoria de registros JSON."""
    value = container.get(key)

    if not isinstance(value, list):
        raise TypeError(
            f"{key} debe ser una lista.",
        )

    records: list[JSONObject] = []

    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise TypeError(
                f"{key}[{index}] debe ser un objeto JSON.",
            )

        records.append(
            cast(JSONObject, item),
        )

    return records


def normalize_records(
    records: list[JSONObject],
) -> pd.DataFrame:
    """Normaliza una lista de objetos JSON."""
    return pd.json_normalize(
        records,
        sep=".",
    )


def require_columns(
    frame: pd.DataFrame,
    columns: set[str],
    *,
    source: str,
) -> None:
    """Comprueba que un DataFrame tenga las columnas esperadas."""
    missing = columns.difference(frame.columns)

    if missing:
        missing_text = ", ".join(
            sorted(missing),
        )
        raise ValueError(
            f"{source} no contiene las columnas: "
            f"{missing_text}.",
        )


def summarize_active_trials(
    trials: pd.DataFrame,
) -> dict[str, int]:
    """Cuenta los ensayos activos por país."""
    require_columns(
        trials,
        {
            "nct_id",
            "overall_status",
            "countries",
        },
        source="ClinicalTrials.gov",
    )

    active = trials.loc[
        trials["overall_status"].isin(
            ACTIVE_TRIAL_STATUSES,
        ),
        [
            "nct_id",
            "overall_status",
            "countries",
        ],
    ].explode(
        "countries",
        ignore_index=True,
    )

    counts: dict[str, int] = {}

    for country, count in (
        active["countries"]
        .dropna()
        .astype("string")
        .value_counts()
        .items()
    ):
        counts[str(country)] = int(count)

    return counts


def summarize_reactions(
    events: pd.DataFrame,
) -> dict[str, int]:
    """Cuenta las reacciones notificadas en openFDA."""
    require_columns(
        events,
        {
            "safety_report_id",
            "reactions",
        },
        source="openFDA",
    )

    exploded = events[
        [
            "safety_report_id",
            "reactions",
        ]
    ].explode(
        "reactions",
        ignore_index=True,
    )

    counts: dict[str, int] = {}

    for reaction, count in (
        exploded["reactions"]
        .dropna()
        .astype("string")
        .value_counts()
        .items()
    ):
        counts[str(reaction)] = int(count)

    return counts


def summarize_publications(
    articles: pd.DataFrame,
) -> dict[str, int]:
    """Cuenta los artículos de PubMed por año."""
    require_columns(
        articles,
        {
            "pmid",
            "publication_year",
        },
        source="PubMed",
    )

    counts: dict[str, int] = {}

    for year, count in (
        articles["publication_year"]
        .dropna()
        .astype("int64")
        .value_counts()
        .sort_index()
        .items()
    ):
        counts[str(year)] = int(count)

    return counts


def print_mapping(
    mapping: dict[str, int],
    *,
    empty_message: str,
) -> None:
    """Imprime un conteo ordenado o un mensaje vacío."""
    if not mapping:
        print(empty_message)
        return

    for label, count in mapping.items():
        print(f"{label}: {count}")


def main() -> None:
    """Ejecuta la consolidación local."""
    project_root = Path(__file__).resolve().parents[1]
    report_path = (
        project_root
        / "data"
        / "processed"
        / "validation_report.json"
    )
    output_dir = (
        project_root
        / "data"
        / "processed"
    )

    report = load_json_object(
        report_path,
    )
    valid_records = require_object(
        report,
        "valid_records",
    )

    trial_records = require_records(
        valid_records,
        "clinicaltrials",
    )
    pubmed_records = require_records(
        valid_records,
        "pubmed",
    )
    openfda_records = require_records(
        valid_records,
        "openfda",
    )

    trials = normalize_records(
        trial_records,
    )
    articles = normalize_records(
        pubmed_records,
    )
    events = normalize_records(
        openfda_records,
    )

    require_columns(
        trials,
        {
            "nct_id",
            "overall_status",
            "start_date",
            "countries",
        },
        source="ClinicalTrials.gov",
    )
    require_columns(
        articles,
        {
            "pmid",
            "publication_year",
            "authors",
        },
        source="PubMed",
    )
    require_columns(
        events,
        {
            "safety_report_id",
            "receipt_date",
            "drugs",
            "reactions",
        },
        source="openFDA",
    )

    trials["start_year"] = pd.to_numeric(
        trials["start_date"].str[:4],
        errors="coerce",
    ).astype(
        "Int64",
    )

    events["receipt_date"] = pd.to_datetime(
        events["receipt_date"],
        errors="raise",
    )
    events["transmission_date"] = pd.to_datetime(
        events["transmission_date"],
        errors="coerce",
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    parquet_paths = {
        "clinicaltrials": (
            output_dir
            / "clinicaltrials.parquet"
        ),
        "pubmed": (
            output_dir
            / "pubmed.parquet"
        ),
        "openfda": (
            output_dir
            / "openfda.parquet"
        ),
    }

    trials.to_parquet(
        parquet_paths["clinicaltrials"],
        index=False,
    )
    articles.to_parquet(
        parquet_paths["pubmed"],
        index=False,
    )
    events.to_parquet(
        parquet_paths["openfda"],
        index=False,
    )

    active_by_country = summarize_active_trials(
        trials,
    )
    reaction_counts = summarize_reactions(
        events,
    )
    publications_by_year = summarize_publications(
        articles,
    )

    analysis = {
        "records": {
            "clinicaltrials": len(trials),
            "pubmed": len(articles),
            "openfda": len(events),
        },
        "questions": {
            "active_trials_by_country": (
                active_by_country
            ),
            "openfda_reactions": (
                reaction_counts
            ),
            "pubmed_publications_by_year": (
                publications_by_year
            ),
        },
    }

    analysis_path = (
        output_dir
        / "analysis_summary.json"
    )
    analysis_path.write_text(
        json.dumps(
            analysis,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("===== DATAFRAMES =====")
    print(
        "ClinicalTrials.gov:",
        trials.shape,
    )
    print(
        "PubMed:",
        articles.shape,
    )
    print(
        "openFDA:",
        events.shape,
    )

    print(
        "\n===== PARQUET =====",
    )

    for source, path in parquet_paths.items():
        print(
            f"{source}: "
            f"{path.relative_to(project_root)}"
        )

    print(
        "\n===== PREGUNTA 1: "
        "ENSAYOS ACTIVOS POR PAÍS =====",
    )
    print_mapping(
        active_by_country,
        empty_message=(
            "No hay ensayos activos en la "
            "muestra validada."
        ),
    )

    print(
        "\n===== PREGUNTA 2: "
        "REACCIONES OPENFDA =====",
    )
    print_mapping(
        reaction_counts,
        empty_message=(
            "No hay reacciones en la muestra."
        ),
    )

    print(
        "\n===== PREGUNTA 3: "
        "PUBLICACIONES POR AÑO =====",
    )
    print_mapping(
        publications_by_year,
        empty_message=(
            "No hay publicaciones en la muestra."
        ),
    )

    print(
        "\nResumen:",
        analysis_path.relative_to(
            project_root,
        ),
    )


if __name__ == "__main__":
    main()
