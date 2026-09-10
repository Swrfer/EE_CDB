"""Validated joins for clinical tables."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def merge_with_patient_data(
    records: pd.DataFrame,
    patients: pd.DataFrame,
    *,
    record_patient_id: str = "PATIENT",
    patient_id: str = "Id",
    patient_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Join clinical records with patient data using many-to-one validation.

    Parameters
    ----------
    records
        Clinical records containing a patient identifier. Measurements retain
        their original units; this function performs no unit conversion.
    patients
        Patient-level table expected to contain one row per patient.
    record_patient_id
        Identifier column in the clinical records.
    patient_id
        Identifier column in the patient table.
    patient_columns
        Optional patient columns to append. The identifier is included
        automatically.

    Returns
    -------
    pandas.DataFrame
        Joined table preserving the rows and order of ``records``.

    Raises
    ------
    ValueError
        If an identifier or requested column is absent, or if patient
        identifiers are duplicated.
    """
    if record_patient_id not in records.columns:
        raise ValueError(f"Missing record identifier: {record_patient_id}")
    if patient_id not in patients.columns:
        raise ValueError(f"Missing patient identifier: {patient_id}")
    if patients[patient_id].duplicated().any():
        raise ValueError("Patient identifiers must be unique")

    if patient_columns is None:
        selected_columns = list(patients.columns)
    else:
        selected_columns = [patient_id]
        selected_columns.extend(
            column for column in patient_columns if column != patient_id
        )

    missing = sorted(set(selected_columns).difference(patients.columns))
    if missing:
        raise ValueError("Missing requested patient columns: " + ", ".join(missing))

    patient_data = patients[selected_columns].copy()

    return records.merge(
        patient_data,
        how="left",
        left_on=record_patient_id,
        right_on=patient_id,
        validate="many_to_one",
        sort=False,
    )
