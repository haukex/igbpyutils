#!/bin/bash
set -euxo pipefail
# Must pass filename for pip to install as first argument
test -n "$1"
DISTFILE="$(realpath "$1")"
test -f "$DISTFILE"

cd "$( dirname "${BASH_SOURCE[0]}" )"/..

TEMPDIR="$( mktemp --directory )"
trap 'set +e; popd; rm -rf "$TEMPDIR"' EXIT

rsync -a tests $TEMPDIR --exclude=__pycache__

pushd "$TEMPDIR"
python3 -m venv venv
venv/bin/python3 -m pip -q install "$DISTFILE"
venv/bin/python3 -Im unittest

