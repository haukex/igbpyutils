#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

for PY_DOCK in 3.9-bookworm 3.10-bookworm 3.11-bookworm 3.12-bookworm; do  # not yet: 3.13-rc-bookworm
    docker run --rm -it -v "$PWD":/usr/src/igbpyutils -w /usr/src/igbpyutils "python:$PY_DOCK" \
        bash -c 'pip install --root-user-action=ignore -r requirements.txt -r dev/requirements.txt && ./prove.sh'
done
