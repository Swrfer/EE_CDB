"""Utilities for reproducible clinical data analysis."""

from clinlab.cleaning import convert_numeric_observations
from clinlab.clinical import egfr_ckd_epi_2021
from clinlab.demographics import classify_age_group
from clinlab.joins import merge_with_patient_data
from clinlab.validation import (
    find_duplicate_patient_ids,
    flag_impossible_encounters,
    flag_patient_sentinels,
)

__all__ = [
    "classify_age_group",
    "convert_numeric_observations",
    "egfr_ckd_epi_2021",
    "find_duplicate_patient_ids",
    "flag_impossible_encounters",
    "flag_patient_sentinels",
    "merge_with_patient_data",
]
