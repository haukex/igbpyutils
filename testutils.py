#!python3
"""Some utilities for testing.

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
import sys
import os
from copy import deepcopy
from typing import TypeVar, Generic
from contextlib import contextmanager
from collections.abc import Generator
from tempfile import NamedTemporaryFile

# noinspection PyPep8Naming
@contextmanager
def MyNamedTempFile(*args, **kwargs) -> Generator:
    """A ``NamedTemporaryFile`` that is unlinked on context manager exit, not on close.

    TODO Later: Deprecate this function when Python 3.12 is released; users should then
    use ``NamedTemporaryFile(delete=True, delete_on_close=False)`` instead."""
    if sys.hexversion>=0x030C00F0:
        # noinspection PyArgumentList
        yield NamedTemporaryFile(*args, **kwargs, delete=True, delete_on_close=False)  # pragma: no cover
    else:
        tf = NamedTemporaryFile(*args, **kwargs, delete=False)
        try: yield tf
        finally: os.unlink(tf.name)

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
