#!/usr/bin/env python3
"""Generate .coveragerc3.X files (development tool)

Note the arguments specified on the command line are the minor version number,
for example ``gencovrc.py 9 13`` generates the files for Python 3.9 to 3.12.

Author, Copyright, and License
------------------------------
Copyright (c) 2023 Hauke Daempfling (haukex@zero-g.net)
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
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description='Generate .coveragerc3.X files')
parser.add_argument('-f','--forver',metavar='VERSION', help="only generate for this version")
parser.add_argument('-q','--quiet',help="Don't output informational messages",action="store_true")
parser.add_argument('min_ver', type=int, metavar="MINVER", help="3.N minimum version (inclusive)")
parser.add_argument('max_ver', type=int, metavar="MAXVER", help="3.M maximum version (exclusive)")
args = parser.parse_args()

VERSIONS = range(args.min_ver, args.max_ver)
if args.forver:
    forver = -1
    if re.fullmatch(r'''\A[0-9]+\Z''', args.forver):
        forver = int(args.forver)
    elif m := re.fullmatch(r'''\A3.([0-9]+)\Z''', args.forver):
        forver = int(m.group(1))
    else:
        parser.error("--forver must be either 3.X format or minor version number only")
    if forver not in VERSIONS:
        parser.error("--forver must be in the MINVER and MAXVER range")
    RCFILES = (forver,)
else:
    RCFILES = VERSIONS

for vc in RCFILES:
    fn = Path(__file__).parent.parent / f".coveragerc3.{vc}"
    with fn.open('w', encoding='ASCII', newline='\n') as fh:
        print(f"# .coveragerc for Python 3.{vc}\n[report]\nexclude_lines =\n    pragma: no cover", file=fh)
        for v in VERSIONS[1:]:
            print(f"    cover-req-" + re.escape(f"{'ge' if v>vc else 'lt'}3.{v}"), file=fh)
    if not args.quiet:
        print(f"Wrote {fn.name}")
