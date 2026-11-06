#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
exec "${ATLAS_PYTHON:-./.venv/bin/python}" -B -m atlas_engine.storage.http "$@"
