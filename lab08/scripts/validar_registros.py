"""Valida registros reales y casos malformados controlados."""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from clientes.adapters import (
    JSONObject,
    clinical_trial_from_api,
    openfda_event_from_api,
    pubmed_record_from_esummary,
    require_list,
    require_object,
    require_string,
)

RecordModel = TypeVar(
    "RecordModel",
    bound=BaseModel,
)
Adapter = Callable[
    [JSONObject],
    RecordModel,
]


@dataclass(frozen=True, slots=True)
class ValidationFailure:
    """Registro descartado y motivo de su rechazo."""

    source: str
    index: int
    identifier: str
    reason: str


def latest_raw_body(
    raw_root: Path,
    source: str,
) -> Path:
    """Localiza el cuerpo crudo más reciente."""
    candidates = [
        path
        for path in (raw_root / source).glob("*.json")
        if not path.name.endswith(".metadata.json")
    ]

    if not candidates:
        raise FileNotFoundError(
            f"No hay datos crudos para {source}."
        )

    return max(
        candidates,
        key=lambda path: path.stat().st_mtime_ns,
    )


def load_json_object(path: Path) -> JSONObject:
    """Carga un cuerpo JSON guardado."""
    payload: object = json.loads(
        path.read_text(encoding="utf-8")
    )

    return require_object(
        payload,
        str(path),
    )


def clinical_trial_records(
    payload: JSONObject,
) -> list[JSONObject]:
    """Extrae el arreglo studies."""
    values = require_list(
        payload.get("studies"),
        "studies",
    )

    return [
        require_object(
            value,
            f"studies[{index}]",
        )
        for index, value in enumerate(values)
    ]


def openfda_records(
    payload: JSONObject,
) -> list[JSONObject]:
    """Extrae el arreglo results de openFDA."""
    values = require_list(
        payload.get("results"),
        "results",
    )

    return [
        require_object(
            value,
            f"results[{index}]",
        )
        for index, value in enumerate(values)
    ]


def pubmed_records(
    payload: JSONObject,
) -> list[JSONObject]:
    """Extrae entradas ESummary en el orden de uids."""
    result = require_object(
        payload.get("result"),
        "result",
    )

    uid_values = require_list(
        result.get("uids"),
        "result.uids",
    )

    records: list[JSONObject] = []

    for index, uid_value in enumerate(uid_values):
        uid = require_string(
            uid_value,
            f"result.uids[{index}]",
        )

        records.append(
            require_object(
                result.get(uid),
                f"result.{uid}",
            )
        )

    return records


def record_identifier(
    source: str,
    raw: JSONObject,
    index: int,
) -> str:
    """Obtiene un identificador útil para el registro."""
    if source.startswith("clinicaltrials"):
        try:
            protocol = require_object(
                raw.get("protocolSection"),
                "protocolSection",
            )
            identification = require_object(
                protocol.get(
                    "identificationModule"
                ),
                "identificationModule",
            )
            return require_string(
                identification.get("nctId"),
                "nctId",
            )
        except ValueError:
            pass

    if source.startswith("pubmed"):
        value = raw.get("uid")

        if isinstance(value, str) and value:
            return value

    if source.startswith("openfda"):
        value = raw.get("safetyreportid")

        if isinstance(value, str) and value:
            return value

    return f"{source}[{index}]"


def validate_batch[RecordModel: BaseModel](
    *,
    source: str,
    raw_records: list[JSONObject],
    adapter: Adapter[RecordModel],
) -> tuple[
    list[RecordModel],
    list[ValidationFailure],
]:
    """Valida, conserva registros válidos y registra fallos."""
    valid: list[RecordModel] = []
    failures: list[ValidationFailure] = []

    for index, raw in enumerate(raw_records):
        identifier = record_identifier(
            source,
            raw,
            index,
        )

        try:
            record = adapter(raw)
        except (
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            failures.append(
                ValidationFailure(
                    source=source,
                    index=index,
                    identifier=identifier,
                    reason=" | ".join(
                        str(error).splitlines()
                    ),
                )
            )
            continue

        valid.append(record)

    return valid, failures


def malformed_controls(
    *,
    trials: list[JSONObject],
    articles: list[JSONObject],
    events: list[JSONObject],
) -> dict[str, list[JSONObject]]:
    """Crea tres copias dañadas de manera controlada."""
    if not trials or not articles or not events:
        raise ValueError(
            "Se necesita un registro real de cada fuente."
        )

    invalid_trial = deepcopy(trials[0])
    trial_protocol = require_object(
        invalid_trial["protocolSection"],
        "protocolSection",
    )
    trial_design = require_object(
        trial_protocol["designModule"],
        "designModule",
    )
    trial_enrollment = require_object(
        trial_design["enrollmentInfo"],
        "enrollmentInfo",
    )
    trial_enrollment.pop(
        "count",
        None,
    )

    invalid_article = deepcopy(articles[0])
    invalid_article["title"] = ""

    invalid_event = deepcopy(events[0])
    invalid_patient = require_object(
        invalid_event["patient"],
        "patient",
    )
    invalid_patient["reaction"] = []

    return {
        "clinicaltrials_control": [
            invalid_trial
        ],
        "pubmed_control": [
            invalid_article
        ],
        "openfda_control": [
            invalid_event
        ],
    }


def print_report(
    *,
    source: str,
    received: int,
    valid: int,
    failures: list[ValidationFailure],
) -> None:
    """Imprime un resumen legible."""
    print(f"===== {source.upper()} =====")
    print("Recibidos:", received)
    print("Válidos:", valid)
    print("Descartados:", len(failures))

    for failure in failures:
        print(
            "FALLO:",
            failure.identifier,
            "|",
            failure.reason,
        )


def main() -> None:
    """Ejecuta la validación real y controlada."""
    project_root = Path(__file__).resolve().parents[1]
    raw_root = project_root / "data" / "raw"
    processed_root = project_root / "data" / "processed"

    processed_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    trial_payload = load_json_object(
        latest_raw_body(
            raw_root,
            "clinicaltrials",
        )
    )
    pubmed_payload = load_json_object(
        latest_raw_body(
            raw_root,
            "pubmed_summary",
        )
    )
    openfda_payload = load_json_object(
        latest_raw_body(
            raw_root,
            "openfda",
        )
    )

    trials = clinical_trial_records(
        trial_payload
    )
    articles = pubmed_records(
        pubmed_payload
    )
    events = openfda_records(
        openfda_payload
    )

    valid_trials, trial_failures = validate_batch(
        source="clinicaltrials",
        raw_records=trials,
        adapter=clinical_trial_from_api,
    )
    valid_articles, article_failures = validate_batch(
        source="pubmed",
        raw_records=articles,
        adapter=pubmed_record_from_esummary,
    )
    valid_events, event_failures = validate_batch(
        source="openfda",
        raw_records=events,
        adapter=openfda_event_from_api,
    )

    print("===== REGISTROS REALES =====")

    print_report(
        source="clinicaltrials",
        received=len(trials),
        valid=len(valid_trials),
        failures=trial_failures,
    )
    print_report(
        source="pubmed",
        received=len(articles),
        valid=len(valid_articles),
        failures=article_failures,
    )
    print_report(
        source="openfda",
        received=len(events),
        valid=len(valid_events),
        failures=event_failures,
    )

    controls = malformed_controls(
        trials=trials,
        articles=articles,
        events=events,
    )

    control_results = (
        (
            "clinicaltrials_control",
            controls["clinicaltrials_control"],
            clinical_trial_from_api,
        ),
        (
            "pubmed_control",
            controls["pubmed_control"],
            pubmed_record_from_esummary,
        ),
        (
            "openfda_control",
            controls["openfda_control"],
            openfda_event_from_api,
        ),
    )

    control_failures: list[
        ValidationFailure
    ] = []

    print("===== CONTROLES MALFORMADOS =====")

    for source, records, adapter in control_results:
        valid, failures = validate_batch(
            source=source,
            raw_records=records,
            adapter=adapter,
        )

        control_failures.extend(
            failures
        )

        print_report(
            source=source,
            received=len(records),
            valid=len(valid),
            failures=failures,
        )

    actual_failures = (
        trial_failures
        + article_failures
        + event_failures
    )

    report = {
        "actual": {
            "received": (
                len(trials)
                + len(articles)
                + len(events)
            ),
            "valid": (
                len(valid_trials)
                + len(valid_articles)
                + len(valid_events)
            ),
            "failures": [
                asdict(failure)
                for failure in actual_failures
            ],
        },
        "controlled_malformed": {
            "received": 3,
            "valid": 0,
            "failures": [
                asdict(failure)
                for failure in control_failures
            ],
        },
        "valid_records": {
            "clinicaltrials": [
                record.model_dump(mode="json")
                for record in valid_trials
            ],
            "pubmed": [
                record.model_dump(mode="json")
                for record in valid_articles
            ],
            "openfda": [
                record.model_dump(mode="json")
                for record in valid_events
            ],
        },
    }

    report_path = (
        processed_root
        / "validation_report.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("===== RESUMEN =====")
    print(
        "Registros reales recibidos:",
        len(trials) + len(articles) + len(events),
    )
    print(
        "Registros reales válidos:",
        len(valid_trials) + len(valid_articles) + len(valid_events),
    )
    print(
        "Fallos reales:",
        len(actual_failures),
    )
    print(
        "Controles malformados rechazados:",
        len(control_failures),
    )
    print(
        "Informe:",
        report_path.relative_to(
            project_root
        ),
    )


if __name__ == "__main__":
    main()
