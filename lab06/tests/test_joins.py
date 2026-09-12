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


def test_union_conserva_filas_orden_y_datos_originales(
    malicious_patients: pd.DataFrame,
) -> None:
    """Attach patient data without multiplying or modifying records."""
    # Motivo: uniones many-to-one auditadas por bloques en el lab 2.
    patients = malicious_patients.iloc[[0, 1]].copy()
    records = pd.DataFrame(
        {
            "PATIENT": ["p2", "p1", "p1", "unknown"],
            "record_id": ["r1", "r2", "r3", "r4"],
        }
    )
    original_records = records.copy(deep=True)
    original_patients = patients.copy(deep=True)

    result = merge_with_patient_data(
        records,
        patients,
        patient_id="person_id",
        patient_columns=["age"],
    )

    assert len(result) == len(records)
    assert result["record_id"].tolist() == ["r1", "r2", "r3", "r4"]
    assert result["age"].iloc[:3].tolist() == pytest.approx([12, 45, 45])
    assert pd.isna(result["age"].iloc[3])
    assert "hba1c" not in result.columns

    pd.testing.assert_frame_equal(records, original_records)
    pd.testing.assert_frame_equal(patients, original_patients)


def test_rechaza_pacientes_duplicados_antes_de_multiplicar_filas(
    malicious_patients: pd.DataFrame,
) -> None:
    """Reject duplicate patient keys before performing the join."""
    # Motivo: auditoría de duplicados del lab 2; allí no se encontraron.
    records = pd.DataFrame({"PATIENT": ["p4"]})

    with pytest.raises(
        ValueError,
        match="Patient identifiers must be unique",
    ):
        merge_with_patient_data(
            records,
            malicious_patients,
            patient_id="person_id",
        )


def test_union_con_registros_vacios_devuelve_esquema_coherente(
    malicious_patients: pd.DataFrame,
) -> None:
    """Return an empty result with the expected columns."""
    # Motivo: procesamiento por bloques del lab 2; vacío preventivo.
    records = pd.DataFrame(
        {
            "PATIENT": pd.Series(dtype="object"),
            "record_id": pd.Series(dtype="object"),
        }
    )
    patients = malicious_patients.iloc[[0, 1]].copy()

    result = merge_with_patient_data(
        records,
        patients,
        patient_id="person_id",
        patient_columns=["age"],
    )

    assert result.empty
    assert set(result.columns) == {
        "PATIENT",
        "record_id",
        "person_id",
        "age",
    }


def test_rechaza_columna_de_paciente_solicitada_que_no_existe(
    malicious_patients: pd.DataFrame,
) -> None:
    """Report a missing requested column with a clear error."""
    patients = malicious_patients.iloc[[0]].copy()
    records = pd.DataFrame({"PATIENT": ["p1"]})

    with pytest.raises(
        ValueError,
        match="Missing requested patient columns: nonexistent",
    ):
        merge_with_patient_data(
            records,
            patients,
            patient_id="person_id",
            patient_columns=["nonexistent"],
        )
