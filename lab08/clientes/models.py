"""Modelos Pydantic para las tres fuentes biomédicas."""

from __future__ import annotations

import calendar
import re
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

PARTIAL_DATE_PATTERN = re.compile(
    r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$"
)


class TrialStatus(StrEnum):
    """Estados conocidos de ClinicalTrials.gov."""

    NOT_YET_RECRUITING = "NOT_YET_RECRUITING"
    RECRUITING = "RECRUITING"
    ENROLLING_BY_INVITATION = "ENROLLING_BY_INVITATION"
    ACTIVE_NOT_RECRUITING = "ACTIVE_NOT_RECRUITING"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    COMPLETED = "COMPLETED"
    WITHDRAWN = "WITHDRAWN"
    UNKNOWN = "UNKNOWN"
    AVAILABLE = "AVAILABLE"
    NO_LONGER_AVAILABLE = "NO_LONGER_AVAILABLE"
    TEMPORARILY_NOT_AVAILABLE = "TEMPORARILY_NOT_AVAILABLE"
    APPROVED_FOR_MARKETING = "APPROVED_FOR_MARKETING"


def partial_date_bounds(value: str) -> tuple[date, date]:
    """Convierte YYYY, YYYY-MM o YYYY-MM-DD en un intervalo."""
    if not PARTIAL_DATE_PATTERN.fullmatch(value):
        raise ValueError(
            "La fecha debe usar YYYY, YYYY-MM o YYYY-MM-DD."
        )

    parts = [int(part) for part in value.split("-")]
    year = parts[0]

    if len(parts) == 1:
        return (
            date(year, 1, 1),
            date(year, 12, 31),
        )

    month = parts[1]

    if len(parts) == 2:
        last_day = calendar.monthrange(
            year,
            month,
        )[1]

        return (
            date(year, month, 1),
            date(year, month, last_day),
        )

    exact = date(
        year,
        month,
        parts[2],
    )

    return exact, exact


class ClinicalTrialRecord(BaseModel):
    """Registro normalizado de ClinicalTrials.gov."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    nct_id: str = Field(
        pattern=r"^NCT\d{8}$"
    )
    title: str = Field(
        min_length=1
    )
    overall_status: TrialStatus
    enrollment_count: int = Field(
        ge=0
    )
    start_date: str | None = None
    completion_date: str | None = None
    countries: list[str] = Field(
        default_factory=list
    )

    @field_validator(
        "start_date",
        "completion_date",
    )
    @classmethod
    def validate_partial_date(
        cls,
        value: str | None,
    ) -> str | None:
        """Valida fechas completas o parciales."""
        if value is not None:
            partial_date_bounds(value)

        return value

    @field_validator("countries")
    @classmethod
    def validate_countries(
        cls,
        values: list[str],
    ) -> list[str]:
        """Rechaza países vacíos."""
        if any(not value.strip() for value in values):
            raise ValueError(
                "Los países no pueden estar vacíos."
            )

        return values

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        """Comprueba que el inicio no siga a la finalización."""
        if (
            self.start_date is None
            or self.completion_date is None
        ):
            return self

        start_earliest, _ = partial_date_bounds(
            self.start_date
        )
        _, completion_latest = partial_date_bounds(
            self.completion_date
        )

        if start_earliest > completion_latest:
            raise ValueError(
                "start_date ocurre después de completion_date."
            )

        return self


class PubMedRecord(BaseModel):
    """Registro bibliográfico normalizado de PubMed."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    pmid: str = Field(
        pattern=r"^\d+$"
    )
    title: str = Field(
        min_length=1
    )
    publication_year: int = Field(
        ge=1800
    )
    journal: str | None = None
    authors: list[str] = Field(
        default_factory=list
    )

    @field_validator("publication_year")
    @classmethod
    def validate_publication_year(
        cls,
        value: int,
    ) -> int:
        """Rechaza años bibliográficos inverosímiles."""
        maximum = datetime.now(UTC).year + 1

        if value > maximum:
            raise ValueError(
                f"publication_year no puede superar {maximum}."
            )

        return value

    @field_validator("authors")
    @classmethod
    def validate_authors(
        cls,
        values: list[str],
    ) -> list[str]:
        """Rechaza nombres de autor vacíos."""
        if any(not value.strip() for value in values):
            raise ValueError(
                "Los autores no pueden estar vacíos."
            )

        return values


class OpenFDAEvent(BaseModel):
    """Reporte normalizado de evento adverso de openFDA."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    safety_report_id: str = Field(
        pattern=r"^\d+$"
    )
    receipt_date: date
    transmission_date: date | None = None
    serious: bool
    drugs: list[str] = Field(
        min_length=1
    )
    reactions: list[str] = Field(
        min_length=1
    )
    patient_age_years: float | None = Field(
        default=None,
        ge=0,
        le=130,
    )

    @field_validator(
        "receipt_date",
        "transmission_date",
        mode="before",
    )
    @classmethod
    def parse_fda_date(
        cls,
        value: Any,
    ) -> Any:
        """Convierte fechas FAERS con formato YYYYMMDD."""
        if value is None or isinstance(value, date):
            return value

        if not isinstance(value, str):
            raise TypeError(
                "La fecha openFDA debe ser texto YYYYMMDD."
            )

        try:
            return datetime.strptime(
                value,
                "%Y%m%d",
            ).date()
        except ValueError as error:
            raise ValueError(
                "La fecha openFDA debe usar YYYYMMDD."
            ) from error

    @field_validator(
        "drugs",
        "reactions",
    )
    @classmethod
    def validate_nonempty_terms(
        cls,
        values: list[str],
    ) -> list[str]:
        """Rechaza nombres clínicos vacíos."""
        if any(not value.strip() for value in values):
            raise ValueError(
                "Los términos clínicos no pueden estar vacíos."
            )

        return values

    @model_validator(mode="after")
    def validate_event_dates(self) -> Self:
        """Valida temporalidad del reporte."""
        today = datetime.now(UTC).date()

        if self.receipt_date > today:
            raise ValueError(
                "receipt_date no puede estar en el futuro."
            )

        if (
            self.transmission_date is not None
            and self.transmission_date < self.receipt_date
        ):
            raise ValueError(
                "transmission_date precede a receipt_date."
            )

        return self
