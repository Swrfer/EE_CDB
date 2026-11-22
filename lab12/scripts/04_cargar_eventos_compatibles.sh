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
  lab12/scripts/04_cargar_eventos_compatibles.R \
  2>&1 \
  | tee lab12/evidencias/08_carga_eventos_compatibles.txt
