"""Development Utility Functions

Author, Copyright, and License
------------------------------
Copyright (c) 2023-2024 Hauke Daempfling (haukex@zero-g.net)
at the Leibniz Institute of Freshwater Ecology and Inland Fisheries (IGB),
Berlin, Germany, https://www.igb-berlin.de/

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see https://www.gnu.org/licenses/
"""
import re
import sys
import warnings
from pathlib import Path
from typing import Optional
# reexport:
from .script_vs_lib import check_script_vs_lib as check_script_vs_lib  # noqa: F401

def generate_coveragerc(*,  # pragma: no cover
                        minver :int, maxver :int, forver :Optional[int]=None, outdir :Optional[Path]=None, verbose :bool=False):
    """Generate ``.coveragerc3.X`` files for various Python 3 versions.

    .. deprecated:: 0.8.0
        Use https://pypi.org/project/coverage-simple-excludes/ instead.

    These generated files provide tags such as ``cover-req-ge3.10`` and ``cover-req-lt3.10`` that can be used
    to exclude source code lines on ranges of Python versions. This tool is used within this project itself.
    In addition, the tags ``cover-linux``, ``cover-win32``, and ``cover-darwin`` are supplied based on ``sys.platform``
    for code for which coverage is only expected on those OSes (more such tags could be added in the future).
    Because the generated files use the ``exclude_also`` config option, Coverage.py 7.2.0 or greater is required.

    :param minver: The minimum Python minor version which to include in the generated tags, inclusive.
    :param maxver: The maximum Python minor version which to include in the generated tags, exclusive.
    :param forver: If specified, only a single ``.coverage3.X`` file for that minor version is generated,
        otherwise files are generated for all versions in the aforementioned range.
    :param outdir: The path into which to output the files. Defaults to the current working directory.
    :param verbose: If true, ``print`` a message for each file written.
    """
    warnings.warn("Use coverage-simple-excludes instead", DeprecationWarning)
    versions = range(minver, maxver)
    if not versions:
        raise ValueError("No versions in range")
    if forver is not None and forver not in versions:
        raise ValueError("forver must be in the range minver to maxver")
    if not outdir:
        outdir = Path()
    for vc in versions if forver is None else (forver,):
        fn = outdir / f".coveragerc3.{vc}"
        with fn.open('x', encoding='ASCII', newline='\n') as fh:
            print(f"# Generated .coveragerc for Python 3.{vc}\n[report]\nexclude_also =", file=fh)
            if not sys.platform.startswith('linux'):
                print("    cover-linux", file=fh)
            if not sys.platform.startswith('win32'):
                print("    cover-win32", file=fh)
            if not sys.platform.startswith('darwin'):
                print("    cover-darwin", file=fh)
            for v in versions[1:]:
                print("    cover-req-" + re.escape(f"{'ge' if v>vc else 'lt'}3.{v}"), file=fh)
        if verbose:
            print(f"Wrote {fn}")
