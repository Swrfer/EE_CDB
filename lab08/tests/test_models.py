"""Pruebas de los modelos Pydantic biomédicos."""

from datetime import date

import pytest
from pydantic import ValidationError

from clientes.models import (
    ClinicalTrialRecord,
    OpenFDAEvent,
    PubMedRecord,
    TrialStatus,
)


def test_valid_clinical_trial_accepts_partial_dates() -> None:
    """Un ensayo válido puede usar fechas parciales."""
    record = ClinicalTrialRecord(
        nct_id="NCT01234567",
        title="A gastric cancer trial",
        overall_status=TrialStatus.COMPLETED,
        enrollment_count=88,
        start_date="2020-03",
        completion_date="2022",
        countries=["Mexico", "United States"],
    )

    assert record.enrollment_count == 88
    assert record.start_date == "2020-03"


def test_trial_rejects_missing_enrollment() -> None:
    """La inscripción es un campo clínico obligatorio."""
    with pytest.raises(
        ValidationError,
        match="enrollment_count",
    ):
        ClinicalTrialRecord.model_validate(
            {
                "nct_id": "NCT01234567",
                "title": "Incomplete trial",
                "overall_status": "COMPLETED",
            }
        )


def test_trial_rejects_negative_enrollment() -> None:
    """El número de participantes no puede ser negativo."""
    with pytest.raises(
        ValidationError,
        match="greater than or equal to 0",
    ):
        ClinicalTrialRecord(
            nct_id="NCT01234567",
            title="Invalid enrollment",
            overall_status=TrialStatus.RECRUITING,
            enrollment_count=-1,
        )


def test_trial_rejects_reversed_dates() -> None:
    """La finalización no puede preceder al inicio."""
    with pytest.raises(
        ValidationError,
        match=(
            "start_date ocurre después de "
            "completion_date"
        ),
    ):
        ClinicalTrialRecord(
            nct_id="NCT01234567",
            title="Invalid dates",
            overall_status=TrialStatus.COMPLETED,
            enrollment_count=10,
            start_date="2025-10-01",
            completion_date="2020-12-31",
        )


def test_trial_rejects_unknown_status() -> None:
    """El estado debe pertenecer al conjunto conocido."""
    with pytest.raises(
        ValidationError,
        match="UNKNOWN_NEW_STATUS",
    ):
        ClinicalTrialRecord.model_validate(
            {
                "nct_id": "NCT01234567",
                "title": "Invalid status",
                "overall_status": "UNKNOWN_NEW_STATUS",
                "enrollment_count": 10,
            }
        )


def test_valid_pubmed_record() -> None:
    """Un registro bibliográfico coherente es aceptado."""
    record = PubMedRecord(
        pmid="42826542",
        title="Epigenetic regulation in gastric cancer",
        publication_year=2026,
        journal="Cancer Research",
        authors=["García A", "Researcher B"],
    )

    assert record.publication_year == 2026
    assert len(record.authors) == 2


def test_pubmed_rejects_empty_title() -> None:
    """Un artículo sin título no cruza la frontera."""
    with pytest.raises(
        ValidationError,
        match="title",
    ):
        PubMedRecord(
            pmid="42826542",
            title="",
            publication_year=2026,
        )


def test_valid_openfda_event() -> None:
    """Un reporte FAERS válido convierte sus fechas."""
    record = OpenFDAEvent.model_validate(
        {
            "safety_report_id": "10004141",
            "receipt_date": "20150310",
            "transmission_date": "20150318",
            "serious": True,
            "drugs": ["GLEEVEC"],
            "reactions": ["Hepatic lesion"],
            "patient_age_years": 62,
        }
    )

    assert record.receipt_date == date(2015, 3, 10)
    assert record.transmission_date == date(2015, 3, 18)


def test_openfda_rejects_empty_reactions() -> None:
    """Un reporte sin reacciones no es analizable."""
    with pytest.raises(
        ValidationError,
        match="reactions",
    ):
        OpenFDAEvent.model_validate(
            {
                "safety_report_id": "10004141",
                "receipt_date": "20150310",
                "serious": True,
                "drugs": ["GLEEVEC"],
                "reactions": [],
            }
        )


def test_openfda_rejects_impossible_age() -> None:
    """La edad normalizada debe estar entre 0 y 130 años."""
    with pytest.raises(
        ValidationError,
        match="less than or equal to 130",
    ):
        OpenFDAEvent.model_validate(
            {
                "safety_report_id": "10004141",
                "receipt_date": "20150310",
                "serious": True,
                "drugs": ["GLEEVEC"],
                "reactions": ["Hepatic lesion"],
                "patient_age_years": 250,
            }
        )
