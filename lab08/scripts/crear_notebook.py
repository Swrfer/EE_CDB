"""Genera el notebook reproducible de consolidación."""

from __future__ import annotations

from pathlib import Path

import nbformat


def markdown(text: str) -> object:
    """Crea una celda Markdown."""
    return nbformat.v4.new_markdown_cell(
        text.strip(),
    )


def code(text: str) -> object:
    """Crea una celda de código."""
    return nbformat.v4.new_code_cell(
        text.strip(),
    )


def main() -> None:
    """Construye el notebook consolidado."""
    project_root = Path(__file__).resolve().parents[1]
    notebook_path = (
        project_root
        / "notebooks"
        / "consolidado.ipynb"
    )

    cells = [
        markdown(
            """
# Laboratorio 08: consolidación de APIs biomédicas

Este notebook integra los registros validados de
ClinicalTrials.gov, PubMed y openFDA para la condición
**cáncer gástrico**.

Los resultados corresponden a una muestra pequeña de tres
registros por fuente. Por ello, las conclusiones demuestran
el funcionamiento técnico del pipeline y no representan
estimaciones epidemiológicas ni clínicas generales.
"""
        ),
        markdown(
            """
## 1. Cargar los archivos Parquet

Los archivos se generaron únicamente después de conservar
las respuestas crudas, adaptar sus estructuras y validar
cada registro mediante Pydantic.
"""
        ),
        code(
            """
from pathlib import Path

import pandas as pd
from IPython.display import display


def find_project_root(start: Path) -> Path:
    candidates = [start, *start.parents]

    for candidate in candidates:
        if (
            (candidate / "pyproject.toml").exists()
            and (candidate / "clientes").is_dir()
        ):
            return candidate

    raise FileNotFoundError(
        "No se encontró la raíz del Laboratorio 08."
    )


project_root = find_project_root(
    Path.cwd().resolve()
)
processed = project_root / "data" / "processed"

trials = pd.read_parquet(
    processed / "clinicaltrials.parquet"
)
articles = pd.read_parquet(
    processed / "pubmed.parquet"
)
events = pd.read_parquet(
    processed / "openfda.parquet"
)

print("ClinicalTrials.gov:", trials.shape)
print("PubMed:", articles.shape)
print("openFDA:", events.shape)
"""
        ),
        markdown(
            """
## 2. Inspección de los datos normalizados
"""
        ),
        code(
            """
display(
    trials[
        [
            "nct_id",
            "overall_status",
            "enrollment_count",
            "countries",
        ]
    ]
)

display(
    articles[
        [
            "pmid",
            "publication_year",
            "journal",
            "title",
        ]
    ]
)

display(
    events[
        [
            "safety_report_id",
            "serious",
            "drugs",
            "reactions",
        ]
    ]
)
"""
        ),
        markdown(
            """
## 3. Pregunta 1: ¿cuántos ensayos activos hay y dónde?

Se consideran activos los estados `RECRUITING`,
`NOT_YET_RECRUITING`, `ENROLLING_BY_INVITATION` y
`ACTIVE_NOT_RECRUITING`.
"""
        ),
        code(
            """
active_statuses = {
    "ACTIVE_NOT_RECRUITING",
    "ENROLLING_BY_INVITATION",
    "NOT_YET_RECRUITING",
    "RECRUITING",
}

active_trials = trials.loc[
    trials["overall_status"].isin(active_statuses),
    [
        "nct_id",
        "overall_status",
        "countries",
    ],
].explode(
    "countries",
    ignore_index=True,
)

active_by_country = (
    active_trials["countries"]
    .dropna()
    .value_counts()
    .rename_axis("country")
    .reset_index(name="active_trials")
)

if active_by_country.empty:
    print(
        "No hay ensayos activos en la muestra validada."
    )
else:
    display(active_by_country)
"""
        ),
        markdown(
            """
**Resultado:** ninguno de los tres ensayos de la muestra
presentó un estado considerado activo. Dos estaban
completados y uno tenía estado desconocido. Este resultado
solo describe la muestra utilizada.
"""
        ),
        markdown(
            """
## 4. Pregunta 2: ¿cuáles fueron las reacciones más reportadas?

Las listas de reacciones se expanden para contar cada
término de manera independiente.
"""
        ),
        code(
            """
reaction_counts = (
    events[
        [
            "safety_report_id",
            "reactions",
        ]
    ]
    .explode(
        "reactions",
        ignore_index=True,
    )["reactions"]
    .dropna()
    .value_counts()
    .rename_axis("reaction")
    .reset_index(name="reports")
)

display(reaction_counts)
"""
        ),
        markdown(
            """
**Resultado:** `Pyrexia` apareció en dos reportes. Las
demás reacciones aparecieron una vez. Los reportes de
openFDA son notificaciones de farmacovigilancia y no
demuestran causalidad entre un medicamento y una reacción.
"""
        ),
        markdown(
            """
## 5. Pregunta 3: ¿cómo se distribuyen las publicaciones por año?
"""
        ),
        code(
            """
publications_by_year = (
    articles["publication_year"]
    .value_counts()
    .sort_index()
    .rename_axis("publication_year")
    .reset_index(name="articles")
)

display(publications_by_year)
"""
        ),
        markdown(
            """
**Resultado:** los tres artículos recuperados fueron
publicados en 2026. La muestra se obtuvo de los primeros
resultados de una consulta ordenada por la API y no debe
interpretarse como la evolución histórica completa de la
literatura sobre cáncer gástrico.
"""
        ),
        markdown(
            """
## 6. Conclusiones

El pipeline integró correctamente tres fuentes con
estructuras distintas y produjo tablas Parquet que pueden
reutilizarse sin consultar nuevamente las APIs.

En esta muestra no hubo ensayos activos, `Pyrexia` fue la
única reacción repetida y los tres artículos correspondieron
a 2026. La utilidad principal de este análisis es demostrar
una ruta reproducible que posteriormente puede ampliarse a
consultas por genes, pronóstico y regulación epigenética.
"""
        ),
    ]

    notebook = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python (cdb)",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.12",
            },
        },
    )

    notebook_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    nbformat.write(
        notebook,
        notebook_path,
    )

    print(
        "Notebook creado:",
        notebook_path.relative_to(
            project_root,
        ),
    )


if __name__ == "__main__":
    main()
