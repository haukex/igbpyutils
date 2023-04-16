#!/bin/bash
set -euo pipefail
# Utility script for running tests/coverage on all Python versions locally
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
if [ "$OSTYPE" == "msys" ]; then  # e.g. Git bash on Windows
  for PY_VER in Python39 Python310 Python311; do
    PYTHON="$HOME/AppData/Local/Programs/Python/$PY_VER/python"
    echo "===== Running" "$PYTHON" "====="
    PYTHONWARNDEFAULTENCODING=1 "$PYTHON" -m unittest "$@"
  done
else  # Linux
  for PY_VER in 3.9 3.10 3.11 3.12; do
    PYTHON="/opt/python$PY_VER/bin/python3"
    echo "===== Running" "$PYTHON" "====="
    COVERAGE="/opt/python$PY_VER/bin/coverage"
    PYTHONWARNDEFAULTENCODING=1 "$COVERAGE" run --rcfile=".coveragerc$PY_VER" --branch -m unittest "$@"
    "$COVERAGE" report --rcfile=".coveragerc$PY_VER" --skip-covered --show-missing --fail-under=100 | grep -v 'skipped due to complete coverage'
    "$COVERAGE" erase
    git clean -xf htmlcov
  done
fi
