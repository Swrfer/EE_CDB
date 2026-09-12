"""Tests for the specific sentinel values required by the laboratory."""

import pandas as pd
import pytest

from clinlab import flag_patient_sentinels


def test_detecta_centinelas_sin_eliminar_pacientes(
    malicious_patients: pd.DataFrame,
) -> None:
    """Flag the sentinel row while preserving the original data."""
    # Lab 2: auditoría de valores; centinelas introducidos por el enunciado.
    original = malicious_patients.copy(deep=True)

    result = flag_patient_sentinels(malicious_patients)

    expected = [False, False, False, False, False, True, False]
    assert result["age_sentinel"].tolist() == expected
    assert result["hba1c_sentinel"].tolist() == expected
    assert len(result) == len(original)

    pd.testing.assert_frame_equal(malicious_patients, original)
    pd.testing.assert_frame_equal(result[original.columns], original)


def test_no_confunde_faltantes_con_centinelas() -> None:
    """Keep missing values distinct from explicit sentinel values."""
    # Lab 2: los faltantes se analizaron según el significado de cada variable.
    patients = pd.DataFrame(
        {
            "age": pd.Series([pd.NA, pd.NA], dtype="Float64"),
            "hba1c": pd.Series([pd.NA, pd.NA], dtype="Float64"),
        }
    )

    result = flag_patient_sentinels(patients)

    assert not result["age_sentinel"].any()
    assert not result["hba1c_sentinel"].any()
    assert result["age"].isna().all()
    assert result["hba1c"].isna().all()


def test_centinelas_en_tabla_vacia_conservan_esquema() -> None:
    """Return empty Boolean flags when the input contains no rows."""
    # Lab 2: procesamiento por bloques; entrada vacía preventiva.
    patients = pd.DataFrame(
        {
            "age": pd.Series(dtype="Float64"),
            "hba1c": pd.Series(dtype="Float64"),
        }
    )

    result = flag_patient_sentinels(patients)

    assert result.empty
    assert str(result["age_sentinel"].dtype) == "bool"
    assert str(result["hba1c_sentinel"].dtype) == "bool"


@pytest.mark.parametrize("missing_column", ["age", "hba1c"])
def test_centinelas_requieren_ambas_columnas(missing_column: str) -> None:
    """Report absent input columns."""
    patients = pd.DataFrame({"age": [45], "hba1c": [7.1]}).drop(
        columns=[missing_column]
    )

    with pytest.raises(
        ValueError,
        match=f"Missing required columns: {missing_column}",
    ):
        flag_patient_sentinels(patients)
