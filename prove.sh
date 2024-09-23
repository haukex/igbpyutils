#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
if [ "$OSTYPE" == "msys" ]; then  # e.g. Git bash on Windows
  PYTHONWARNINGS=error PYTHONWARNDEFAULTENCODING=1 python3 -m unittest "$@"
else
  PY_VER="$( python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' )"
  python3 -c 'from igbpyutils.dev import generate_coveragerc_cli as main; main()' -q -f"$PY_VER" 9 13
  PYTHONWARNINGS=error PYTHONWARNDEFAULTENCODING=1 coverage run --rcfile=".coveragerc$PY_VER" --branch -m unittest "$@"
  coverage report --rcfile=".coveragerc$PY_VER" --omit='*/igbdatatools/*' --skip-covered --show-missing --fail-under=100 | grep -v 'skipped due to complete coverage'
  coverage erase
  git clean -xf htmlcov
  rm -f ".coveragerc$PY_VER"
  mypy --python-version "$PY_VER" igbpyutils tests
fi
