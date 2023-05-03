#!python3
"""A few useful iterators.

Note the iterator ``gray_product`` that used to be in this module
has been merged into ``more_itertools`` as of version 9.1.0.

Author, Copyright, and License
------------------------------
Copyright (c) 2022-2023 Hauke Daempfling (haukex@zero-g.net)
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
from collections.abc import Sized, Iterator, Iterable, Callable, Generator
from typing import TypeVar, Generic, Optional, Any, overload
from itertools import tee, zip_longest

_marker = object()
_T0 = TypeVar('_T0')
_T1 = TypeVar('_T1')
_T2 = TypeVar('_T2')
@overload
def zip_strict(__iter1: Iterable[_T1]) -> Iterator[tuple[_T1]]: ...  # pragma: no cover
@overload
def zip_strict(
    __iter1: Iterable[_T1], __iter2: Iterable[_T2]
) -> Iterator[tuple[_T1, _T2]]: ...  # pragma: no cover
@overload
def zip_strict(
    __iter1: Iterable[_T0],
    __iter2: Iterable[_T0],
    __iter3: Iterable[_T0],
    *iterables: Iterable[_T0],
) -> Iterator[tuple[_T0, ...]]: ...  # pragma: no cover
def zip_strict(*iterables):  # cover-not-ge3.10
    """Like Python's ``zip``, but requires all iterables to return the same number of items."""
    for combo in zip_longest(*iterables, fillvalue=_marker):
        if any( v is _marker for v in combo ):
            raise ValueError("Iterables have different lengths")
        yield combo
if sys.hexversion>=0x030A00F0:  # cover-not-le3.9
    from functools import partial
    zip_strict = partial(zip, strict=True)  # type: ignore
else: pass  # cover-not-ge3.10

_T = TypeVar('_T', covariant=True)
class SizedCallbackIterator(Generic[_T], Sized, Iterator[_T]):
    """Wrapper to add ``len`` support to an iterator.

    For example, this can be used to wrap a generator which has a known output length
    (e.g. if it returns exactly one item per input item), so that it can then
    be used in libraries like ``tqdm``."""
    def __init__(self, it :Iterable[_T], length :int, *, strict :bool=False, callback :Optional[Callable[[int, _T], None]]=None):
        if length<0: raise ValueError("length must be >= 0")
        self.it = iter(it)
        self.length = length
        self._count = 0
        self.strict = strict
        self.callback = callback
    def __len__(self) -> int: return self.length
    def __iter__(self) -> Iterator[_T]: return self
    def __next__(self) -> _T:
        try:
            val :_T = next(self.it)
        except StopIteration as ex:
            if self.strict and self._count != self.length:
                raise ValueError(f"expected iterator to return {self.length} items, but it returned {self._count}") from ex
            raise ex
        else:
            if self.callback:
                self.callback(self._count, val)
            self._count += 1
            return val

_V = TypeVar('_V', covariant=True)
def is_unique_everseen(iterable :Iterable[_V], *, key :Optional[Callable[[_V], Any]] = None) -> Generator[bool, None, None]:
    """For each element in the input iterable, return either ``True`` if this
    element is unique, or ``False`` if it is not.

    The implementation is very similar :func:`more_itertools.unique_everseen`
    and is subject to the same performance considerations.
    """
    seen_set = set()
    seen_list = []
    for element in iterable:
        k = element if key is None else key(element)
        try:
            if k not in seen_set:
                seen_set.add(k)
                yield True
            else:
                yield False
        except TypeError:
            if k not in seen_list:
                seen_list.append(k)
                yield True
            else:
                yield False

def no_duplicates(iterable :Iterable[_V], *, key :Optional[Callable[[_V], Any]] = None, name :str="item") -> Generator[_V, None, None]:
    """Raise a ``ValueError`` if there are any duplicate elements in the
    input iterable.

    Remember that if you don't want to use this iterator's return values,
    but only use it for checking a list, you need to force it to execute
    by wrapping the call e.g. in a ``set()`` or ``list()``.
    Alternatively, use ``not all(is_unique_everseen(iterable))``.

    The ``name`` argument is only to customize the error messages.

    :func:`more_itertools.duplicates_everseen` could also be used for this purpose,
    but this function returns the values of the input iterable.

    The implementation is very similar :func:`more_itertools.unique_everseen`
    and is subject to the same performance considerations.
    """
    it1, it2 = tee(iterable)
    for element, unique in zip_strict(it1, is_unique_everseen(it2, key=key)):
        if not unique: raise ValueError(f"duplicate {name}: {element!r}")
        else: yield element
