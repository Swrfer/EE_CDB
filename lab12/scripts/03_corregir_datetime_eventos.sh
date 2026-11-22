#!/usr/bin/env bash

set -euo pipefail

RAIZ="$(
  git rev-parse \
    --show-toplevel
)"

cd "$RAIZ"

JAVA_HOME="$(
  java \
    -XshowSettings:properties \
    -version \
    2>&1 \
  | awk \
      -F'= ' \
      '/^[[:space:]]*java.home = / {
        print $2
        exit
      }'
)"

export JAVA_HOME

caffeinate \
  -i \
  Rscript \
  lab12/scripts/03_corregir_datetime_eventos.R \
  2>&1 \
  | tee lab12/evidencias/07_correccion_datetime_eventos.txt
