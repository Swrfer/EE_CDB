#!/usr/bin/env bash

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [[ "$(git branch --show-current)" != "lab12-omop-cdm" ]]; then
  echo "ERROR: la rama actual no es lab12-omop-cdm"
  exit 1
fi

if [[ -f lab12/scripts/06_comparar_eunomia.R ]]; then
  mkdir -p lab12/evidencias/intentos_fallidos
  mv \
    lab12/scripts/06_comparar_eunomia.R \
    lab12/evidencias/intentos_fallidos/06_comparar_eunomia_R_fallido.R
fi

python - <<'PY'
from pathlib import Path

ruta = Path(".gitignore")
lineas = ruta.read_text(encoding="utf-8").splitlines() if ruta.exists() else []

for entrada in ("/lab12/data/", "*.duckdb", "__pycache__/", "*.py[cod]"):
    if entrada not in lineas:
        lineas.append(entrada)

ruta.write_text("\n".join(lineas).rstrip() + "\n", encoding="utf-8")
PY

validar() {
  echo "Fecha: $(date)"
  echo "Rama: $(git branch --show-current)"
  echo

  echo "1. Sintaxis Python"
  python -m py_compile \
    lab12/scripts/05_generar_analisis.py \
    lab12/scripts/06_comparar_eunomia.py
  echo "PASS"
  echo

  echo "2. Archivos obligatorios"
  for archivo in \
    lab12/README.md \
    lab12/consultas_omop.sql \
    lab12/diagrama_er.md \
    lab12/reporte_calidad.md \
    lab12/evidencias/analisis/calidad_mapeo.csv \
    lab12/evidencias/analisis/ventana_observacion.csv \
    lab12/evidencias/analisis/athena_top3.csv \
    lab12/evidencias/analisis/comparacion_synthea_eunomia.csv
  do
    test -s "$archivo"
    echo "PASS: $archivo"
  done
  echo

  echo "3. Conteos OMOP"
  python - <<'PY'
import duckdb

con = duckdb.connect(
    "lab12/data/omop/synthea_omop_cdm54.duckdb",
    read_only=True,
)

esperados = {
    "concept": 2_026_160,
    "person": 5_745,
    "observation_period": 5_745,
    "visit_occurrence": 320_853,
    "condition_occurrence": 92_084,
    "drug_exposure": 280_617,
    "measurement": 3_111_032,
    "observation": 1_596_434,
    "procedure_occurrence": 385_657,
}

for tabla, esperado in esperados.items():
    obtenido = con.execute(
        f"SELECT COUNT(*) FROM cdm.{tabla}"
    ).fetchone()[0]
    if obtenido != esperado:
        raise SystemExit(
            f"FAIL: {tabla}: esperado={esperado}, obtenido={obtenido}"
        )
    print(f"PASS: {tabla} = {obtenido}")

con.close()
PY
  echo

  echo "4. Calidad de mapeo"
  python - <<'PY'
import pandas as pd

calidad = pd.read_csv("lab12/evidencias/analisis/calidad_mapeo.csv")
if not (calidad["porcentaje_concept_id_cero"] == 0).all():
    raise SystemExit("FAIL: se encontraron concept_id igual a cero")
print("PASS: seis dominios con 0% de concept_id = 0")
PY
  echo

  echo "5. Ventana de observación"
  python - <<'PY'
import pandas as pd

ventana = pd.read_csv("lab12/evidencias/analisis/ventana_observacion.csv")
assert ventana.loc[0, "eventos_sin_filtrar"] == 92084
assert ventana.loc[0, "eventos_fuera_observacion"] == 699
print("PASS: efecto de observation_period cuantificado")
PY
  echo

  echo "6. Comparación Eunomia"
  python - <<'PY'
import pandas as pd

comparacion = pd.read_csv(
    "lab12/evidencias/analisis/comparacion_synthea_eunomia.csv"
)
assert len(comparacion) == 7
assert {"synthea_propio", "eunomia"}.issubset(comparacion.columns)
print("PASS: siete métricas comparativas")
PY
  echo
  echo "RESULTADO FINAL: PASS"
}

mkdir -p lab12/evidencias
validar 2>&1 | tee lab12/evidencias/14_validacion_final.txt

echo "===== COMPROBAR DATOS IGNORADOS ====="
git check-ignore \
  lab12/data/omop/synthea_omop_cdm54.duckdb \
  lab12/data/reference/eunomia_gibleed.duckdb \
  lab12/data/reference/eunomia_cache/GiBleed_5.3.zip

echo "===== PREPARAR COMMIT ====="
git add .gitignore lab12

if git diff --cached --name-only | grep -E '(^lab12/data/|\.duckdb$|\.zip$)'; then
  echo "ERROR: se intentaron incluir datos pesados en Git"
  exit 1
fi

git diff --cached --check -- . ':(exclude)lab12/evidencias/**'

demasiado_grande=0
while IFS= read -r archivo; do
  [[ -n "$archivo" ]] || continue
  tamano="$(git cat-file -s ":$archivo" 2>/dev/null || echo 0)"
  if (( tamano > 20000000 )); then
    echo "ERROR: archivo mayor de 20 MB: $archivo ($tamano bytes)"
    demasiado_grande=1
  fi
done < <(git diff --cached --name-only --diff-filter=ACMR)

if (( demasiado_grande != 0 )); then
  exit 1
fi

echo "===== ARCHIVOS PREPARADOS ====="
git diff --cached --stat

echo "===== CREAR COMMIT ====="
git commit -m "feat(lab12): complete OMOP CDM conversion and quality analysis"

echo "===== PUBLICAR RAMA ====="
git push --set-upstream origin lab12-omop-cdm

echo "===== RESULTADO ====="
git status --short --branch
git log -1 --oneline --decorate
