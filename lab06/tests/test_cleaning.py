"""Tests for numeric and qualitative clinical observations."""

import pandas as pd
import pytest

from clinlab import convert_numeric_observations


def test_convierte_numericos_y_conserva_observaciones_cualitativas() -> None:
    """Convert numeric values without changing source values or units."""
    # Lab 2: los valores TYPE=text eran observaciones cualitativas válidas.
    observations = pd.DataFrame(
        {
            "VALUE": ["7.1", "positive", "bad", "12"],
            "TYPE": ["numeric", "text", "numeric", "text"],
            "UNITS": ["%", None, "%", None],
        },
        index=[10, 20, 30, 40],
    )
    original = observations.copy(deep=True)

    result = convert_numeric_observations(observations)

    assert result.loc[10, "VALUE_NUMERIC"] == pytest.approx(7.1)
    assert result.loc[[20, 30, 40], "VALUE_NUMERIC"].isna().all()
    assert str(result["VALUE_NUMERIC"].dtype) == "Float64"
    pd.testing.assert_frame_equal(observations, original)
    pd.testing.assert_frame_equal(result[original.columns], original)


def test_columna_de_valores_completamente_faltantes() -> None:
    """Keep missing numeric observations as missing."""
    # Lab 2: auditoría de faltantes; columna totalmente vacía como caso preventivo.
    observations = pd.DataFrame(
        {
            "VALUE": [None, None],
            "TYPE": ["numeric", "numeric"],
        }
    )

    result = convert_numeric_observations(observations)

    assert len(result) == 2
    assert result["VALUE_NUMERIC"].isna().all()
    assert str(result["VALUE_NUMERIC"].dtype) == "Float64"


def test_observaciones_vacias_conservan_esquema() -> None:
    """Return an empty numeric column for an empty input."""
    # Lab 2: procesamiento por bloques; resultado vacío como caso preventivo.
    observations = pd.DataFrame(
        {
            "VALUE": pd.Series(dtype="string"),
            "TYPE": pd.Series(dtype="string"),
        }
    )

    result = convert_numeric_observations(observations)

    assert result.empty
    assert list(result.columns) == ["VALUE", "TYPE", "VALUE_NUMERIC"]
    assert str(result["VALUE_NUMERIC"].dtype) == "Float64"


@pytest.mark.parametrize("missing_column", ["VALUE", "TYPE"])
def test_rechaza_observaciones_sin_columna_requerida(
    missing_column: str,
) -> None:
    """Report missing input columns explicitly."""
    observations = pd.DataFrame({"VALUE": ["7.1"], "TYPE": ["numeric"]}).drop(
        columns=[missing_column]
    )

    with pytest.raises(
        ValueError,
        match=f"Missing required columns: {missing_column}",
    ):
        convert_numeric_observations(observations)
