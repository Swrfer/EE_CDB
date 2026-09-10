"""Validation functions for patient and encounter data."""

from __future__ import annotations

import pandas as pd


def find_duplicate_patient_ids(
    patients: pd.DataFrame,
    *,
    id_column: str = "Id",
) -> pd.DataFrame:
    """Return every row associated with a duplicated patient identifier.

    Parameters
    ----------
    patients
        Patient-level table containing one expected row per patient.
    id_column
        Name of the patient identifier column. Identifiers have no units.

    Returns
    -------
    pandas.DataFrame
        Copy containing all occurrences of duplicated identifiers. An input
        without duplicates produces an empty DataFrame with the same columns.

    Raises
    ------
    ValueError
        If the identifier column is absent.
    """
    if id_column not in patients.columns:
        raise ValueError(f"Missing required column: {id_column}")

    duplicate_mask = patients[id_column].duplicated(keep=False)
    return patients.loc[duplicate_mask].copy()


def flag_impossible_encounters(
    encounters: pd.DataFrame,
    patients: pd.DataFrame,
    *,
    encounter_patient_id: str = "PATIENT",
    patient_id: str = "Id",
    start_column: str = "START",
    stop_column: str = "STOP",
    birth_column: str = "BIRTHDATE",
    death_column: str = "DEATHDATE",
) -> pd.DataFrame:
    """Flag encounters occurring outside a patient's lifespan.

    Parameters
    ----------
    encounters
        Encounter table. ``START`` and ``STOP`` represent calendar dates.
    patients
        Patient table. ``BIRTHDATE`` and ``DEATHDATE`` represent calendar
        dates; a missing death date is interpreted as no recorded death.
    encounter_patient_id
        Patient identifier column in the encounter table.
    patient_id
        Patient identifier column in the patient table.
    start_column
        Encounter start-date column.
    stop_column
        Encounter stop-date column.
    birth_column
        Birth-date column.
    death_column
        Death-date column.

        Returns
    -------
    pandas.DataFrame
        Encounters joined with patient dates, plus Boolean columns
        ``visit_before_birth``, ``start_after_death``, ``stop_after_death``,
        ``invalid_start_date``, ``invalid_stop_date``,
        ``invalid_birth_date`` and ``invalid_death_date``.
        Invalid dates are nonmissing input values that cannot be parsed.
        Missing dates are not flagged as invalid. A false chronology flag
        does not establish temporal validity when a required date is
        missing or invalid.

    Raises
    ------
    ValueError
        If a required column is absent or patient identifiers are duplicated.
    """
    encounter_required = {
        encounter_patient_id,
        start_column,
        stop_column,
    }
    patient_required = {
        patient_id,
        birth_column,
        death_column,
    }

    missing_encounter = sorted(encounter_required.difference(encounters.columns))
    missing_patient = sorted(patient_required.difference(patients.columns))

    if missing_encounter:
        raise ValueError("Missing encounter columns: " + ", ".join(missing_encounter))
    if missing_patient:
        raise ValueError("Missing patient columns: " + ", ".join(missing_patient))
    if patients[patient_id].duplicated().any():
        raise ValueError("Patient identifiers must be unique")

    patient_dates = patients[[patient_id, birth_column, death_column]].copy()

    result = encounters.merge(
        patient_dates,
        how="left",
        left_on=encounter_patient_id,
        right_on=patient_id,
        validate="many_to_one",
        sort=False,
    )

    start = pd.to_datetime(result[start_column], errors="coerce")
    stop = pd.to_datetime(result[stop_column], errors="coerce")
    birth = pd.to_datetime(result[birth_column], errors="coerce")
    death = pd.to_datetime(result[death_column], errors="coerce")
    result["invalid_start_date"] = result[start_column].notna() & start.isna()
    result["invalid_stop_date"] = result[stop_column].notna() & stop.isna()
    result["invalid_birth_date"] = result[birth_column].notna() & birth.isna()
    result["invalid_death_date"] = result[death_column].notna() & death.isna()
    result["visit_before_birth"] = start.notna() & birth.notna() & start.lt(birth)
    result["start_after_death"] = start.notna() & death.notna() & start.gt(death)
    result["stop_after_death"] = stop.notna() & death.notna() & stop.gt(death)

    return result
