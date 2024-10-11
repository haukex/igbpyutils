"""Development Utility Functions: Script vs. Library Checker

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
import os
import re
import sys
import ast
import enum
import argparse
import subprocess
from stat import S_IXUSR
from pathlib import Path
from collections.abc import Sequence
from typing import NamedTuple, Union
from igbpyutils.file import Filename, cmdline_rglob, autoglob

class ResultLevel(enum.IntEnum):
    """A severity level enum for :class:`ScriptLibResult`.

    (Note the numeric values are mostly borrowed from :mod:`logging`.)"""
    INFO = 20
    NOTICE = 25
    WARNING = 30
    ERROR = 40

class ScriptLibFlags(enum.Flag):
    """Flags for :class:`ScriptLibResult`.

    .. warning::

        Always use the named flags, do not rely on the integer flag values staying constant,
        as they are automatically generated.
    """
    #: Whether the file has its execute bit set
    EXEC_BIT = enum.auto()
    #: Whether the file has a shebang line
    SHEBANG = enum.auto()
    #: Whether the file contains ``if __name__=='__main__': ...``
    NAME_MAIN = enum.auto()
    #: Whether the file contains statements that make it look like a script
    #: (i.e. anything that's not a ``def``, ``class``, etc.)
    SCRIPT_LIKE = enum.auto()

class ScriptLibResult(NamedTuple):
    """Result class for :func:`check_script_vs_lib`"""
    #: The file that was analyzed
    path :Path
    #: The severity of the result, see :class:`ResultLevel`
    level :ResultLevel
    #: A textual description of the result, with details
    message :str
    #: The individual results of the analysis, see :class:`ScriptLibFlags`
    flags :ScriptLibFlags

_IS_WINDOWS = sys.platform.startswith('win32')
_git_ls_files_re = re.compile(r'''\A([0-7]+) [a-fA-F0-9]{40} \d+\t(.+?)(?:\r?\n|\Z)''')

DEFAULT_SHEBANG_RE = re.compile(r'''\A\#\!/usr(?:/local)?/bin/(?:env +)?python3?\s*\Z''')

def check_script_vs_lib(path :Filename,  # pylint: disable=too-many-return-statements
                        *, known_shebangs :Union[Sequence[str],re.Pattern] = DEFAULT_SHEBANG_RE,
                        exec_from_git :bool = False) -> ScriptLibResult:
    """This function analyzes a Python file to see whether it looks like a library or a script,
    and checks several features of the file for consistency.

    It checks the following points, each of which on their own would indicate the file is a script, but in certain combinations don't make sense.
    It checks whether the file...

    - has its execute bit set (ignored on Windows, unless ``exec_from_git`` is set)
    - has a shebang line (e.g. ``#!/usr/bin/env python3``, see also the ``known_shebangs`` parameter)
    - contains a ``if __name__=='__main__':`` line
    - contains statements other than ``class``, ``def``, etc. in the main body

    :param path: The name of the file to analyze.
    :param known_shebangs: You may provide your own list of shebang lines that this function will recognize here,
        either as a list of strings (without trailing newlines) or a regular expression.
    :param exec_from_git: If you set this to :obj:`True`, then instead of looking at the file's actual mode bits to determine whether the
        exec bit is set, the function will ask ``git`` for the mode bits of the file and use those.
    :return: A :class:`ScriptLibResult` object that indicates what was found and whether there are any inconsistencies.
    """
    pth = Path(path)
    flags = ScriptLibFlags(0)
    with pth.open(encoding='UTF-8') as fh:
        if not _IS_WINDOWS and os.stat(fh.fileno()).st_mode & S_IXUSR:  # cover-not-win32
            flags |= ScriptLibFlags.EXEC_BIT
        source = fh.read()
    ignore_exec_bit = _IS_WINDOWS
    if exec_from_git:
        flags &= ~ScriptLibFlags.EXEC_BIT
        res = subprocess.run(['git','ls-files','--stage',pth.name], cwd=pth.parent,
                             encoding='UTF-8', check=True, capture_output=True)
        assert not res.returncode and not res.stderr
        if m := _git_ls_files_re.fullmatch(res.stdout):
            if m.group(2) != pth.name:
                raise RuntimeError(f"Unexpected git output, filename mismatch {res.stdout!r}")
            if int(m.group(1), 8) & S_IXUSR:
                flags |= ScriptLibFlags.EXEC_BIT
        else:
            raise RuntimeError(f"Failed to parse git output {res.stdout!r} for {pth.name!r}")
        ignore_exec_bit = False
    shebang_line :str = ''
    if source.startswith('#!'):
        shebang_line = source[:source.index('\n')]
        flags |= ScriptLibFlags.SHEBANG
    why_scriptlike :list[str] = []
    for node in ast.iter_child_nodes(ast.parse(source, filename=str(pth))):
        # If(test=Compare(left=Name(id='__name__', ctx=Load()), ops=[Eq()], comparators=[Constant(value='__main__')])
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)  # pylint: disable=too-many-boolean-expressions
                and isinstance(node.test.left, ast.Name) and node.test.left.id=='__name__' and len(node.test.ops)==1
                and isinstance(node.test.ops[0], ast.Eq) and len(node.test.comparators)==1
                and isinstance(node.test.comparators[0], ast.Constant) and node.test.comparators[0].value=='__main__'):
            flags |= ScriptLibFlags.NAME_MAIN
        elif (not isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                    ast.Assign, ast.AnnAssign, ast.Assert))
              # docstring:
              and not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str))):
            why_scriptlike.append(f"{type(node).__name__}@L{node.lineno}")  # type: ignore[attr-defined]
    if why_scriptlike:
        flags |= ScriptLibFlags.SCRIPT_LIKE
    if flags&ScriptLibFlags.SHEBANG and not ( known_shebangs.fullmatch(shebang_line) if isinstance(known_shebangs, re.Pattern)
                                              else shebang_line in known_shebangs ):
        return ScriptLibResult(pth, ResultLevel.WARNING, f"File has unrecognized shebang {shebang_line!r}", flags)
    if flags&ScriptLibFlags.NAME_MAIN and flags&ScriptLibFlags.SCRIPT_LIKE:
        return ScriptLibResult(pth, ResultLevel.ERROR, "File has `if __name__=='__main__'` and looks like a script due to "
                               f"{', '.join(why_scriptlike)}", flags)
    if not flags&ScriptLibFlags.SHEBANG and not flags&ScriptLibFlags.NAME_MAIN and not flags&ScriptLibFlags.SCRIPT_LIKE:
        # looks like a normal library
        if flags&ScriptLibFlags.EXEC_BIT:
            return ScriptLibResult(pth, ResultLevel.ERROR, "File looks like a library but exec bit is set", flags)
        return ScriptLibResult(pth, ResultLevel.INFO, "File looks like a normal library", flags)
    if not flags&ScriptLibFlags.NAME_MAIN and not flags&ScriptLibFlags.SCRIPT_LIKE:
        assert flags&ScriptLibFlags.SHEBANG
        return ScriptLibResult(pth, ResultLevel.ERROR, f"File has shebang{' and exec bit' if flags&ScriptLibFlags.EXEC_BIT else ''} "
                               "but seems to be missing anything script-like", flags)
    assert (flags&ScriptLibFlags.NAME_MAIN or flags&ScriptLibFlags.SCRIPT_LIKE
            ) and not (flags&ScriptLibFlags.NAME_MAIN and flags&ScriptLibFlags.SCRIPT_LIKE)  # xor
    if (flags & ScriptLibFlags.EXEC_BIT or ignore_exec_bit) and flags&ScriptLibFlags.SHEBANG:
        if flags&ScriptLibFlags.SCRIPT_LIKE:
            return ScriptLibResult(pth, ResultLevel.NOTICE, "File looks like a normal script (but could use `if __name__=='__main__'`)", flags)
        return ScriptLibResult(pth, ResultLevel.INFO, "File looks like a normal script", flags)
    missing = ([] if flags & ScriptLibFlags.EXEC_BIT or ignore_exec_bit else ['exec bit']) + ([] if flags & ScriptLibFlags.SHEBANG else ['shebang'])
    assert missing
    why :str = ', '.join(why_scriptlike) if flags&ScriptLibFlags.SCRIPT_LIKE else "`if __name__=='__main__'`"
    return ScriptLibResult(pth, ResultLevel.ERROR, f"File looks like a script (due to {why}) but is missing {' and '.join(missing)}", flags)

def main() -> None:
    """Command-line interface for :func:`check_script_vs_lib`.

    If the module and script have been installed correctly, you should be able to run ``py-check-script-vs-lib -h`` for help."""
    parser = argparse.ArgumentParser(description='Check Python Scripts vs. Libraries')
    parser.add_argument('-v', '--verbose', help="be verbose", action="store_true")
    parser.add_argument('-n', '--notice', help="show notices and include in issue count", action="store_true")
    parser.add_argument('-g', '--exec-git', help="get the exec bit from git", action="store_true")
    parser.add_argument('paths', help="the paths to check (directories searched recursively)", nargs='*')
    #TODO: Add an option to add known shebang lines
    args = parser.parse_args()
    issues :int = 0
    for path in cmdline_rglob(autoglob(args.paths)):
        if not path.is_file() or not path.suffix.lower()=='.py':
            continue
        result = check_script_vs_lib(path, exec_from_git=args.exec_git)
        if result.level>=ResultLevel.WARNING or args.verbose or args.notice and result.level>=ResultLevel.NOTICE:
            print(f"{result.level.name} {result.path}: {result.message}")
        if result.level>=ResultLevel.WARNING or args.notice and result.level>=ResultLevel.NOTICE:
            issues += 1
    parser.exit(issues)
