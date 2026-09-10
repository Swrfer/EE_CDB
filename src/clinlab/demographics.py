"""Pure transformations for patient demographic variables."""

from __future__ import annotations

import pandas as pd


def classify_age_group(ages: pd.Series) -> pd.Series:
    """Classify patient ages into descriptive groups.

    Parameters
    ----------
    ages
        Patient ages measured in completed years. Missing or nonnumeric
        values remain missing in the returned series.

    Returns
    -------
    pandas.Series
        String series containing ``minor``, ``young_adult``,
        ``middle_aged_adult`` or ``older_adult``.
    Raises
    ------
    ValueError
        If any age is negative.
    Notes
    -----
    This function only classifies age. Physiologically implausible ages,
    such as 180 years, must be detected separately by a validation function.
    """
    numeric_ages = pd.to_numeric(ages, errors="coerce")
    if numeric_ages.lt(0).any():
        raise ValueError("Ages must not be negative")
    groups = pd.cut(
        numeric_ages,
        bins=[-float("inf"), 17, 39, 64, float("inf")],
        labels=[
            "minor",
            "young_adult",
            "middle_aged_adult",
            "older_adult",
        ],
    )

    return pd.Series(
        groups,
        index=ages.index,
        name="age_group",
        dtype="string",
    )
