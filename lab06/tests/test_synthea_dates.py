"""Regression tests for the timestamp formats used by Synthea."""

import pandas as pd
from pandas.testing import assert_frame_equal

from clinlab import flag_impossible_encounters


def test_compara_dias_utc_sin_marcar_el_dia_de_defuncion() -> None:
    """Dates use UTC calendar days, not unknown birth/death times."""
    # Lab 2 normalizaba START/STOP y localizaba BIRTHDATE/DEATHDATE a UTC.
    patients = pd.DataFrame(
        {
            "Id": ["p1"],
            "BIRTHDATE": ["2000-01-01"],
            "DEATHDATE": ["2020-01-10"],
        }
    )
    encounters = pd.DataFrame(
        {
            "PATIENT": ["p1"] * 4,
            "START": [
                "2020-01-10T18:00:00Z",
                "2020-01-11T00:01:00Z",
                "1999-12-31T23:59:00Z",
                "2020-01-10T23:30:00-02:00",
            ],
            "STOP": [
                "2020-01-10T19:00:00Z",
                "2020-01-11T01:00:00Z",
                "2000-01-01T00:00:00Z",
                "2020-01-11T02:00:00Z",
            ],
        }
    )
    before = encounters.copy(deep=True)
    result = flag_impossible_encounters(encounters, patients)
    assert result["start_after_death"].tolist() == [False, True, False, True]
    assert result["stop_after_death"].tolist() == [False, True, False, True]
    assert result["visit_before_birth"].tolist() == [False, False, True, False]
    assert not result["invalid_start_date"].any()
    assert_frame_equal(encounters, before)


def test_formatos_iso_mezclados_y_fecha_invalida_conservan_sus_flags() -> None:
    """Parse ISO dates and timestamps together, retaining invalid inputs."""
    # Prevención derivada de fechas de calendario y timestamps del lab 2.
    patients = pd.DataFrame(
        {
            "Id": ["p1"],
            "BIRTHDATE": ["2000-01-01"],
            "DEATHDATE": [None],
        }
    )
    encounters = pd.DataFrame(
        {
            "PATIENT": ["p1"] * 4,
            "START": ["2021-01-01", "2021-01-02T12:00:00Z", "2021-02-30", None],
            "STOP": [None] * 4,
        }
    )
    result = flag_impossible_encounters(encounters, patients)
    assert result["invalid_start_date"].tolist() == [False, False, True, False]
    assert not result["start_after_death"].any()
