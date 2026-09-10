"""Pure transformations for clinical observation values."""

from __future__ import annotations

import pandas as pd


def convert_numeric_observations(
    observations: pd.DataFrame,
    *,
    value_column: str = "VALUE",
    type_column: str = "TYPE",
) -> pd.DataFrame:
    """Convert values explicitly identified as numeric observations.

    Parameters
    ----------
    observations
        Clinical observations. Values retain the units reported in the
        original ``UNITS`` column; this function performs no unit conversion.
    value_column
        Name of the column containing the observed value.
    type_column
        Name of the column identifying whether an observation is numeric.

    Returns
    -------
    pandas.DataFrame
        Copy of the input with a nullable floating-point column named
        ``VALUE_NUMERIC``. Qualitative observations remain missing in that
        new column.

    Raises
    ------
    ValueError
        If either required column is absent.
    """
    required = {value_column, type_column}
    missing = sorted(required.difference(observations.columns))

    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    result = observations.copy()
    numeric_mask = (
        result[type_column].astype("string").str.strip().str.lower().eq("numeric")
    )

    result["VALUE_NUMERIC"] = pd.Series(
        pd.NA,
        index=result.index,
        dtype="Float64",
    )
    result.loc[numeric_mask, "VALUE_NUMERIC"] = pd.to_numeric(
        result.loc[numeric_mask, value_column],
        errors="coerce",
    )

    return result
