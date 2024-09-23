#!/bin/bash
set -euxo pipefail
cd "$( dirname "${BASH_SOURCE[0]}" )"/..

python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
python3 -m pip install --upgrade pip wheel
pip install -r requirements.txt -r dev/requirements.txt
