"""Tests for descriptive age groups."""

import pandas as pd
import pytest

from clinlab import classify_age_group


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (0, "minor"),
        (17, "minor"),
        (18, "young_adult"),
        (39, "young_adult"),
        (40, "middle_aged_adult"),
        (64, "middle_aged_adult"),
        (65, "older_adult"),
        (90, "older_adult"),
    ],
)
def test_clasifica_edades_en_los_limites_de_cada_grupo(
    age: int,
    expected: str,
) -> None:
    """Check the descriptive age boundaries defined by this project."""
    result = classify_age_group(pd.Series([age]))

    assert result.iloc[0] == expected


def test_edades_faltantes_conservan_indice_y_datos_originales() -> None:
    """Keep missing ages unclassified without modifying the input."""
    # Lab 2: auditoría de faltantes; columna completamente vacía preventiva.
    ages = pd.Series(
        [None, None],
        index=["p1", "p2"],
        dtype="Float64",
    )
    original = ages.copy(deep=True)

    result = classify_age_group(ages)

    assert result.isna().all()
    assert result.index.tolist() == ["p1", "p2"]
    assert str(result.dtype) == "string"
    pd.testing.assert_series_equal(ages, original)


def test_edades_vacias_devuelven_serie_vacia_coherente() -> None:
    """Preserve a meaningful output schema for empty input."""
    # Lab 2: procesamiento por bloques; entrada vacía como caso preventivo.
    result = classify_age_group(pd.Series(dtype="Float64"))

    assert result.empty
    assert result.name == "age_group"
    assert str(result.dtype) == "string"


def test_rechaza_edad_negativa() -> None:
    """Reject negative ages instead of classifying them as minors."""
    # Lab 2: coherencia temporal; edad negativa añadida preventivamente.
    with pytest.raises(ValueError, match="Ages must not be negative"):
        classify_age_group(pd.Series([45, -1]))
