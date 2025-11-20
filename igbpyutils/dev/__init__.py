"""Development Utility Functions

Author, Copyright, and License
------------------------------
Copyright (c) 2023-2025 Hauke Daempfling (haukex@zero-g.net)
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
import warnings
from typing import Union
from collections.abc import Sequence
from igbpyutils.file import Filename
from .script_vs_lib import DEFAULT_SHEBANG_RE, ScriptLibResult
from .script_vs_lib import check_script_vs_lib as _check_script_vs_lib

def check_script_vs_lib(path :Filename,
                        *, known_shebangs :Union[Sequence[str],re.Pattern] = DEFAULT_SHEBANG_RE,
                        exec_from_git :bool = False) -> ScriptLibResult:
    warnings.warn('igbpyutils.dev.check_script_vs_lib was renamed to igbpyutils.dev.script_vs_lib.check_script_vs_lib', DeprecationWarning)
    return _check_script_vs_lib(path, known_shebangs=known_shebangs, exec_from_git=exec_from_git)
