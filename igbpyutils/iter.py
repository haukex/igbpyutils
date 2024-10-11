"""A Few Useful Iterators

Note the iterator "``gray_product``" that used to be in this module
has been merged into :mod:`more_itertools` as of its version 9.1.0
as :func:`~more_itertools.gray_product`.

Author, Copyright, and License
------------------------------
Copyright (c) 2022-2024 Hauke Daempfling (haukex@zero-g.net)
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
import warnings
from functools import partial
from itertools import zip_longest
from typing import TypeVar, Generic, Optional, Any, overload
from collections.abc import Sized, Iterator, Iterable, Callable, Generator
from more_itertools import classify_unique

_marker = object()
_T0 = TypeVar('_T0')  # pylint: disable=invalid-name
_T1 = TypeVar('_T1')  # pylint: disable=invalid-name
_T2 = TypeVar('_T2')  # pylint: disable=invalid-name
@overload
def zip_strict(__iter1: Iterable[_T1]) -> Generator[tuple[_T1], None, None]: ...  # pragma: no cover
@overload
def zip_strict(
    __iter1: Iterable[_T1], __iter2: Iterable[_T2]
) -> Generator[tuple[_T1, _T2], None, None]: ...  # pragma: no cover
@overload
def zip_strict(
    __iter1: Iterable[_T0],
    __iter2: Iterable[_T0],
    __iter3: Iterable[_T0],
    *iterables: Iterable[_T0],
) -> Generator[tuple[_T0, ...], None, None]: ...  # pragma: no cover
def zip_strict(*iterables):  # cover-req-lt3.10
    """Like Python's ``zip``, but requires all iterables to return the same number of items.

    On Python >=3.10, this simply calls :func:`zip` with ``strict=True``."""
    for combo in zip_longest(*iterables, fillvalue=_marker):
        if any( v is _marker for v in combo ):
            raise ValueError("Iterables have different lengths")
        yield combo
zip_strict = partial(zip, strict=True) if sys.hexversion>=0x030A00B0 else zip_strict  # type: ignore[assignment]

_T = TypeVar('_T', covariant=True)  # pylint: disable=typevar-name-incorrect-variance
class SizedCallbackIterator(Generic[_T], Sized, Iterator[_T]):
    """Wrapper to add :func:`len` support and a callback to an iterator.

    For example, this can be used to wrap a generator which has a known output length
    (e.g. if it returns exactly one item per input item), so that it can then
    be used in libraries like `tqdm <https://tqdm.github.io/>`_."""
    def __init__(self, it :Iterable[_T], length :int, *, strict :bool=False, callback :Optional[Callable[[int, _T], None]]=None):
        if length<0:
            raise ValueError("length must be >= 0")
        self.it = iter(it)
        self.length = length
        self._count = 0
        self.strict = strict
        self.callback = callback
    def __len__(self) -> int:
        return self.length
    def __iter__(self) -> Iterator[_T]:
        return self
    def __next__(self) -> _T:
        try:
            val :_T = next(self.it)
        except StopIteration as ex:
            if self.strict and self._count != self.length:
                raise ValueError(f"expected iterator to return {self.length} items, but it returned {self._count}") from ex
            raise ex
        if self.callback:
            self.callback(self._count, val)
        self._count += 1
        return val

_V = TypeVar('_V', covariant=True)  # pylint: disable=typevar-name-incorrect-variance
def is_unique_everseen(iterable :Iterable[_V], *, key :Optional[Callable[[_V], Any]] = None) -> Generator[bool, None, None]:
    """For each element in the input iterable, return either :obj:`True` if this
    element is unique, or :obj:`False` if it is not.

    .. deprecated:: 0.5.0
        Use :func:`more_itertools.classify_unique` instead.

    The implementation is very similar :func:`more_itertools.unique_everseen`
    and is subject to the same performance considerations.
    """
    warnings.warn("Use classify_unique from package more-itertools instead", DeprecationWarning)
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
    """Raise a :exc:`ValueError` if there are any duplicate elements in the
    input iterable.

    Remember that if you don't want to use this iterator's return values,
    but only use it for checking a list, you need to force it to execute
    by wrapping the call e.g. in a :class:`set` or :class:`list`.
    Alternatively, use ``not all( ever for e,just,ever in classify_unique(iterable) )``.

    The ``name`` argument is only to customize the error messages.

    :func:`more_itertools.duplicates_everseen` could also be used for this purpose,
    but this function returns the values of the input iterable.

    The implementation is very similar :func:`more_itertools.unique_everseen`
    and is subject to the same performance considerations.
    """
    for element, _uniq_just, uniq_ever in classify_unique(iterable, key=key):
        if not uniq_ever:
            raise ValueError(f"duplicate {name}: {element!r}")
        yield element
