"""Tests for patient identifiers and encounter chronology."""

import pandas as pd
import pytest

from clinlab import (
    find_duplicate_patient_ids,
    flag_impossible_encounters,
)


def test_identifica_todas_las_filas_con_identificador_duplicado(
    malicious_patients: pd.DataFrame,
) -> None:
    """Return both occurrences of the duplicated patient."""
    # Lab 2: se auditaron duplicados; la fixture los introduce preventivamente.
    original = malicious_patients.copy(deep=True)

    result = find_duplicate_patient_ids(
        malicious_patients,
        id_column="person_id",
    )

    assert result.index.tolist() == [3, 4]
    assert result["person_id"].tolist() == ["p4", "p4"]
    pd.testing.assert_frame_equal(malicious_patients, original)


def test_pacientes_sin_duplicados_devuelven_tabla_vacia(
    malicious_patients: pd.DataFrame,
) -> None:
    """Preserve the schema when no duplicates exist."""
    patients = malicious_patients.iloc[[0, 1]].copy()

    result = find_duplicate_patient_ids(
        patients,
        id_column="person_id",
    )

    assert result.empty
    assert result.columns.tolist() == patients.columns.tolist()


def test_detector_de_duplicados_rechaza_columna_ausente() -> None:
    """Require the identifier column."""
    with pytest.raises(
        ValueError,
        match="Missing required column: person_id",
    ):
        find_duplicate_patient_ids(
            pd.DataFrame({"age": [45]}),
            id_column="person_id",
        )


def test_marca_visita_anterior_al_nacimiento_y_eventos_post_defuncion() -> None:
    """Flag chronology problems while retaining every encounter."""
    # Lab 2: hubo eventos postdefunción; visita prenatal añadida preventivamente.
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
                "1999-12-30",
                "2019-05-01",
                "2020-01-11",
                "2020-01-09",
            ],
            "STOP": [
                "1999-12-31",
                "2019-05-02",
                "2020-01-12",
                "2020-01-11",
            ],
        }
    )
    original_encounters = encounters.copy(deep=True)
    original_patients = patients.copy(deep=True)

    result = flag_impossible_encounters(encounters, patients)

    assert len(result) == 4
    assert result["visit_before_birth"].tolist() == [True, False, False, False]
    assert result["start_after_death"].tolist() == [False, False, True, False]
    assert result["stop_after_death"].tolist() == [False, False, True, True]
    pd.testing.assert_frame_equal(encounters, original_encounters)
    pd.testing.assert_frame_equal(patients, original_patients)


def test_sin_defuncion_registrada_no_marca_eventos_post_defuncion() -> None:
    """Do not flag post-death events when no death date is recorded."""
    # Lab 2: DEATHDATE faltante era compatible con pacientes vivos.
    patients = pd.DataFrame(
        {
            "Id": ["p1"],
            "BIRTHDATE": ["2000-01-01"],
            "DEATHDATE": [None],
        }
    )
    encounters = pd.DataFrame(
        {
            "PATIENT": ["p1"],
            "START": ["2025-01-01"],
            "STOP": ["2025-01-02"],
        }
    )

    result = flag_impossible_encounters(encounters, patients)

    assert not result["visit_before_birth"].any()
    assert not result["start_after_death"].any()
    assert not result["stop_after_death"].any()


def test_validacion_temporal_rechaza_pacientes_duplicados(
    malicious_patients: pd.DataFrame,
) -> None:
    """Reject duplicate patient keys before attaching dates."""
    # Lab 2: uniones con cardinalidad many-to-one para evitar multiplicar filas.
    encounters = pd.DataFrame(
        {
            "PATIENT": ["p4"],
            "START": ["2020-01-01"],
            "STOP": ["2020-01-02"],
        }
    )

    with pytest.raises(
        ValueError,
        match="Patient identifiers must be unique",
    ):
        flag_impossible_encounters(
            encounters,
            malicious_patients,
            patient_id="person_id",
        )


def test_distingue_nacimiento_invalido_de_nacimiento_faltante(
    malicious_patients: pd.DataFrame,
) -> None:
    """Flag an impossible calendar date without flagging missing dates."""
    # Lab 2: auditoría temporal; fecha imposible añadida preventivamente.
    patients = malicious_patients.iloc[[0, 2, 6]].copy()
    encounters = pd.DataFrame(
        {
            "PATIENT": ["p1", "p3", "p6"],
            "START": ["2025-01-01"] * 3,
            "STOP": ["2025-01-02"] * 3,
        }
    )

    result = flag_impossible_encounters(
        encounters,
        patients,
        patient_id="person_id",
    )

    assert len(result) == 3
    assert result["invalid_birth_date"].tolist() == [False, False, True]
    assert not result["invalid_death_date"].any()
    assert not result["invalid_start_date"].any()
    assert not result["invalid_stop_date"].any()

    # La fecha original se conserva para poder investigar el problema.
    assert result["BIRTHDATE"].iloc[2] == "1990-02-30"


@pytest.mark.parametrize(
    ("date_column", "flag_column"),
    [
        ("START", "invalid_start_date"),
        ("STOP", "invalid_stop_date"),
        ("BIRTHDATE", "invalid_birth_date"),
        ("DEATHDATE", "invalid_death_date"),
    ],
)
def test_marca_fecha_no_interpretable_en_cada_columna(
    date_column: str,
    flag_column: str,
) -> None:
    """Flag malformed values in each supported date column."""
    # Lab 2: validación de fechas; texto mal formado como caso preventivo.
    patients = pd.DataFrame(
        {
            "Id": ["p1"],
            "BIRTHDATE": ["1980-01-01"],
            "DEATHDATE": ["2025-01-01"],
        }
    )
    encounters = pd.DataFrame(
        {
            "PATIENT": ["p1"],
            "START": ["2020-01-01"],
            "STOP": ["2020-01-02"],
        }
    )

    if date_column in encounters.columns:
        encounters.loc[0, date_column] = "not-a-date"
    else:
        patients.loc[0, date_column] = "not-a-date"

    result = flag_impossible_encounters(encounters, patients)

    assert bool(result.loc[0, flag_column])
