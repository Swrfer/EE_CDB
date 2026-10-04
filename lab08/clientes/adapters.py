"""Adaptadores de JSON anidado a modelos Pydantic."""

from __future__ import annotations

import re
from typing import Any, cast

from clientes.models import (
    ClinicalTrialRecord,
    OpenFDAEvent,
    PubMedRecord,
)

JSONObject = dict[str, Any]

YEAR_PATTERN = re.compile(
    r"\b(18|19|20)\d{2}\b"
)

AGE_TO_YEARS = {
    "800": 10.0,
    "801": 1.0,
    "802": 1.0 / 12.0,
    "803": 1.0 / 52.1429,
    "804": 1.0 / 365.25,
    "805": 1.0 / 8766.0,
}


def require_object(
    value: object,
    field: str,
) -> JSONObject:
    """Exige un objeto JSON."""
    if not isinstance(value, dict):
        raise ValueError(
            f"{field} debe ser un objeto."
        )

    return cast(JSONObject, value)


def require_list(
    value: object,
    field: str,
) -> list[Any]:
    """Exige una lista JSON."""
    if not isinstance(value, list):
        raise ValueError(
            f"{field} debe ser una lista."
        )

    return value


def require_string(
    value: object,
    field: str,
) -> str:
    """Exige texto no vacío."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{field} debe ser texto no vacío."
        )

    return value.strip()


def require_integer(
    value: object,
    field: str,
) -> int:
    """Exige un entero y excluye booleanos."""
    if isinstance(value, bool):
        raise ValueError(
            f"{field} debe ser un entero."
        )

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as error:
            raise ValueError(
                f"{field} debe ser un entero."
            ) from error

    raise ValueError(
        f"{field} debe ser un entero."
    )


def optional_string(
    value: object,
) -> str | None:
    """Devuelve texto limpio o None."""
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(
            "El valor opcional debe ser texto."
        )

    cleaned = value.strip()
    return cleaned or None


def clinical_trial_from_api(
    raw: JSONObject,
) -> ClinicalTrialRecord:
    """Extrae un estudio de ClinicalTrials.gov."""
    protocol = require_object(
        raw.get("protocolSection"),
        "protocolSection",
    )

    identification = require_object(
        protocol.get("identificationModule"),
        "identificationModule",
    )

    status = require_object(
        protocol.get("statusModule"),
        "statusModule",
    )

    design = require_object(
        protocol.get("designModule"),
        "designModule",
    )

    enrollment = require_object(
        design.get("enrollmentInfo"),
        "enrollmentInfo",
    )

    start_struct = require_object(
        status.get("startDateStruct", {}),
        "startDateStruct",
    )

    completion_struct = require_object(
        status.get("completionDateStruct", {}),
        "completionDateStruct",
    )

    contacts = require_object(
        protocol.get(
            "contactsLocationsModule",
            {},
        ),
        "contactsLocationsModule",
    )

    locations = require_list(
        contacts.get("locations", []),
        "locations",
    )

    countries: list[str] = []

    for index, location_value in enumerate(locations):
        location = require_object(
            location_value,
            f"locations[{index}]",
        )

        country = optional_string(
            location.get("country")
        )

        if country is not None and country not in countries:
            countries.append(country)

    return ClinicalTrialRecord.model_validate(
        {
            "nct_id": require_string(
                identification.get("nctId"),
                "nctId",
            ),
            "title": require_string(
                identification.get("briefTitle"),
                "briefTitle",
            ),
            "overall_status": require_string(
                status.get("overallStatus"),
                "overallStatus",
            ),
            "enrollment_count": require_integer(
                enrollment.get("count"),
                "enrollmentInfo.count",
            ),
            "start_date": optional_string(
                start_struct.get("date")
            ),
            "completion_date": optional_string(
                completion_struct.get("date")
            ),
            "countries": countries,
        }
    )


def pubmed_record_from_esummary(
    raw: JSONObject,
) -> PubMedRecord:
    """Extrae un artículo de una entrada ESummary."""
    pmid = require_string(
        raw.get("uid"),
        "uid",
    )

    title = require_string(
        raw.get("title"),
        "title",
    )

    publication_year = extract_publication_year(
        raw
    )

    journal = optional_string(
        raw.get("fulljournalname")
    )

    if journal is None:
        journal = optional_string(
            raw.get("source")
        )

    author_values = require_list(
        raw.get("authors", []),
        "authors",
    )

    authors: list[str] = []

    for index, author_value in enumerate(
        author_values
    ):
        author = require_object(
            author_value,
            f"authors[{index}]",
        )

        name = optional_string(
            author.get("name")
        )

        if name is not None:
            authors.append(name)

    return PubMedRecord.model_validate(
        {
            "pmid": pmid,
            "title": title,
            "publication_year": publication_year,
            "journal": journal,
            "authors": authors,
        }
    )


def extract_publication_year(
    raw: JSONObject,
) -> int:
    """Obtiene el año desde campos ESummary conocidos."""
    for field in (
        "sortpubdate",
        "pubdate",
        "epubdate",
    ):
        value = raw.get(field)

        if not isinstance(value, str):
            continue

        match = YEAR_PATTERN.search(value)

        if match is not None:
            return int(match.group())

    raise ValueError(
        "No se encontró un año de publicación válido."
    )


def openfda_event_from_api(
    raw: JSONObject,
) -> OpenFDAEvent:
    """Extrae un reporte de evento adverso de openFDA."""
    patient = require_object(
        raw.get("patient"),
        "patient",
    )

    drug_values = require_list(
        patient.get("drug"),
        "patient.drug",
    )

    reaction_values = require_list(
        patient.get("reaction"),
        "patient.reaction",
    )

    drugs: list[str] = []

    for index, drug_value in enumerate(drug_values):
        drug = require_object(
            drug_value,
            f"patient.drug[{index}]",
        )

        medicinal_product = optional_string(
            drug.get("medicinalproduct")
        )

        if (
            medicinal_product is not None
            and medicinal_product not in drugs
        ):
            drugs.append(medicinal_product)

    reactions: list[str] = []

    for index, reaction_value in enumerate(
        reaction_values
    ):
        reaction = require_object(
            reaction_value,
            f"patient.reaction[{index}]",
        )

        reaction_name = optional_string(
            reaction.get("reactionmeddrapt")
        )

        if (
            reaction_name is not None
            and reaction_name not in reactions
        ):
            reactions.append(reaction_name)

    return OpenFDAEvent.model_validate(
        {
            "safety_report_id": require_string(
                raw.get("safetyreportid"),
                "safetyreportid",
            ),
            "receipt_date": require_string(
                raw.get("receiptdate"),
                "receiptdate",
            ),
            "transmission_date": optional_string(
                raw.get("transmissiondate")
            ),
            "serious": parse_serious(
                raw.get("serious")
            ),
            "drugs": drugs,
            "reactions": reactions,
            "patient_age_years": patient_age_years(
                patient
            ),
        }
    )


def parse_serious(value: object) -> bool:
    """Convierte el código FAERS de seriedad."""
    if value in {"1", 1}:
        return True

    if value in {"2", 2, False}:
        return False

    raise ValueError(
        "serious debe usar el código 1 o 2."
    )


def patient_age_years(
    patient: JSONObject,
) -> float | None:
    """Normaliza la edad FAERS a años."""
    raw_age = patient.get("patientonsetage")
    raw_unit = patient.get(
        "patientonsetageunit"
    )

    if raw_age is None or raw_unit is None:
        return None

    try:
        age = float(raw_age)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "patientonsetage debe ser numérico."
        ) from error

    unit = str(raw_unit)
    factor = AGE_TO_YEARS.get(unit)

    if factor is None:
        raise ValueError(
            "patientonsetageunit no es reconocido."
        )

    return age * factor
