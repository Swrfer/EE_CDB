"""Small synthetic datasets for testing clinical data validation."""

import pandas as pd
import pytest


@pytest.fixture
def malicious_patients() -> pd.DataFrame:
    """Return seven patient rows with deliberately problematic values.

    Ages are in years; HbA1c values are percentages.
    Dates use YYYY-MM-DD.
    """
    return pd.DataFrame(
        {
            "person_id": ["p1", "p2", "p3", "p4", "p4", "p5", "p6"],
            "age": [45, 12, None, 60, 60, 180, 35],
            "hba1c": [7.1, 5.2, None, 6.8, 6.8, 0.0, 5.5],
            "BIRTHDATE": [
                "1980-01-01",
                "2013-01-01",
                None,
                "1965-01-01",
                "1965-01-01",
                "1845-01-01",
                "1990-02-30",
            ],
            "DEATHDATE": [None] * 7,
        }
    )
