#!python3
"""Some utilities for testing.

Note the ``MyNamedTempFile`` utility has been moved to ``igbpyutils.file.NamedTempFileDeleteLater``.

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
from copy import deepcopy
from typing import TypeVar, Generic

_T = TypeVar('_T')
class tempcopy(Generic[_T]):
    """A simple context manager that provides a temporary ``deepcopy`` of the variable given to it."""
    def __init__(self, obj :_T):
        self.obj = deepcopy(obj)
    def __enter__(self) -> _T:
        return self.obj
    def __exit__(self, *exc):
        del self.obj
        return False  # don't suppress exception
