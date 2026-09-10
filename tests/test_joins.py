"""Tests for patient joins and identifier integrity."""

import pandas as pd
import pytest

from clinlab import merge_with_patient_data


def test_rechaza_identificador_de_paciente_faltante(
    malicious_patients: pd.DataFrame,
) -> None:
    """Reject a missing identifier in the patient master table."""
    # Motivo: auditoría de llaves del lab 2; ausencia añadida como caso preventivo.
    patients = malicious_patients.iloc[[0, 1]].copy()
    patients.loc[patients.index[1], "person_id"] = None

    records = pd.DataFrame(
        {
            "PATIENT": ["p1"],
            "record_id": ["r1"],
        }
    )

    with pytest.raises(
        ValueError,
        match="Patient identifiers must not be missing",
    ):
        merge_with_patient_data(
            records,
            patients,
            patient_id="person_id",
        )
