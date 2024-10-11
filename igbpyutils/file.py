"""File-Related Utility Functions

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
import os
import io
import re
import sys
import stat
import uuid
import typing
import pickle
import warnings
import contextlib
from glob import glob
from pathlib import Path
from gzip import GzipFile
from os.path import expanduser
from contextlib import contextmanager
from typing import Union, TypeVar, Optional
from functools import singledispatch, partial
from collections.abc import Generator, Iterable, Callable
from tempfile import NamedTemporaryFile, TemporaryDirectory
from stat import S_IWUSR, S_IXUSR, S_IMODE, S_ISDIR, S_ISLNK
from more_itertools import classify_unique

# Possible To-Do for Later: an idea: implement something like https://stackoverflow.com/q/12593576

Filename = Union[str, os.PathLike]
"""A type to represent filenames."""

BinaryStream = Union[typing.IO[bytes], io.RawIOBase, io.BufferedIOBase, GzipFile]
"""A type to represent binary file handles."""

AnyPaths = Union[ Filename, bytes, Iterable[ Union[Filename, bytes] ] ]
"""A type to represent any path or iterable of paths.

Can be converted to :class:`~pathlib.Path` objects with :func:`to_Paths`."""
@singledispatch
def _topath(item :Union[Filename,bytes]):
    raise TypeError(f"I don't know how to covert this to a Path: {item!r}")
@_topath.register  # pyright: ignore [reportCallIssue,reportArgumentType,reportUntypedFunctionDecorator]
def _(item :bytes):
    return Path(os.fsdecode(item))
@_topath.register  # pyright: ignore [reportCallIssue,reportArgumentType,reportUntypedFunctionDecorator]
def _(item :str):
    return Path(item)
@_topath.register  # pyright: ignore [reportCallIssue,reportArgumentType,reportUntypedFunctionDecorator]
def _(item :os.PathLike):
    return Path(item)
@singledispatch
def to_Paths(paths :AnyPaths) -> Generator[Path, None, None]:  # pylint: disable=invalid-name
    """Convert various inputs to :class:`~pathlib.Path` objects."""
    # mypy says this: Argument 1 to "iter" has incompatible type
    # "Union[Union[str, PathLike[Any]], bytes, Iterable[Union[Union[str, PathLike[Any]], bytes]]]"; expected
    # "SupportsIter[Iterator[Union[int, str, PathLike[Any], bytes]]]"
    # => I'm not sure where the "int" is coming from, this seems like some kind of misdetection
    yield from map(_topath, iter(paths))  # type: ignore[arg-type]
# I'd like to use Union[bytes, str, os.PathLike] to combine the following three, but apparently singledispatch doesn't support that
@to_Paths.register
def _(paths :bytes) -> Generator[Path, None, None]:
    yield _topath(paths)
@to_Paths.register
def _(paths :str) -> Generator[Path, None, None]:
    yield _topath(paths)
@to_Paths.register
def _(paths :os.PathLike) -> Generator[Path, None, None]:
    yield _topath(paths)

_nixshell_re = re.compile(r'''(?:\A|\\|/)[a-z]{0,5}sh(?i:\.exe)?\Z''')  # bash, zsh, ksh, tcsh, and many more
_winshell_re = re.compile(r'''\b(?:COMMAND\.COM|cmd\.exe)\b''', re.I)

def autoglob(files :Iterable[str], *, force :bool=False) -> Generator[str, None, None]:
    """In Windows ``cmd.exe``, automatically apply :func:`~glob.glob` and :func:`~os.path.expanduser`, otherwise don't change the input.

    For example, take the following script:

    >>> import argparse
    ... from igbpyutils.file import autoglob
    ... parser = argparse.ArgumentParser(description='Example')
    ... parser.add_argument('files', metavar="FILE", help="Files", nargs="+")
    ... args = parser.parse_args()
    ... paths = autoglob(args.files)

    On a normal \\*NIX shell, calling this script as ``python script.py ~/*.py`` would result in
    ``args.files`` being a list of ``"/home/username/filename.py"`` strings if such files exist, or
    otherwise a single element of ``"/home/username/*.py"``. However, in a Windows ``cmd.exe`` shell,
    the aforementioned command always results in ``args.files`` being ``['~/*.py']``. This function
    fixes that, such that the behavior on Windows is the same as on Linux.

    .. note:: This function now uses a heuristic check of the environment variables ``COMSPEC`` and ``SHELL``
        to detect the current shell. Uncommon values in these variables may cause misdetection; please feel
        free to submit patches if the detection does not work on your system.
    """
    likely_nixshell = bool(_nixshell_re.search(os.environ.get('SHELL', '')))
    likely_winshell = bool(_winshell_re.search(os.environ.get('COMSPEC', '')))
    if likely_winshell and not likely_nixshell or force:
        for f in files:
            f = expanduser(f)
            g = glob(f)  # note glob always returns a list
            # If a *NIX glob doesn't match anything, it isn't expanded,
            # while glob() returns an empty list, so we emulate *NIX.
            if g:
                yield from g
            else:
                yield f
    else:
        yield from files

def cmdline_rglob(paths :AnyPaths) -> Generator[Path, None, None]:
    """Given a list of filenames and directories, such as might be given on the command line, return each input item,
    and also return the result of :meth:`Path.rglob('*')<pathlib.Path.rglob>` for each item that is a directory.

    If the given list is empty, use :class:`Path()<pathlib.PurePath>` instead, i.e. the current directory,
    but only its contents are included in the output, not the directory itself;
    to get that you must explicitly pass the directory as an input.

    :meth:`pathlib.Path.absolute` is used to remove duplicates from the output to the best of its ability.
    This is used instead of :meth:`pathlib.Path.resolve` because that resolves symlinks and therefore
    would cause unexpected results for programs that need to see symlinks.

    :seealso: :func:`autoglob` can be used on the list of paths before passing it to this function."""
    def path_gen():
        cnt = 0
        for cnt, pth in enumerate(to_Paths(paths), start=1):
            yield pth
            if pth.is_dir():
                yield from pth.rglob('*')
        if not cnt:
            yield from Path().rglob('*')
    for path, _uniq_just, uniq_ever in classify_unique(path_gen(), key=lambda k: k.absolute()):
        if uniq_ever:
            yield path

class Pushd:  # cover-req-lt3.11
    """A context manager that temporarily changes the current working directory.

    On Python >=3.11, this is simply an alias for :func:`contextlib.chdir`."""
    def __init__(self, newdir :Filename):
        self.newdir = newdir
    def __enter__(self):
        self.prevdir = os.getcwd()  # pylint: disable=attribute-defined-outside-init
        os.chdir(self.newdir)
    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.prevdir)
        return False  # raise exception if any

Pushd = contextlib.chdir if sys.hexversion>=0x030B00B0 else Pushd  # type: ignore[attr-defined, assignment, misc, unused-ignore]

def filetypestr(st :os.stat_result) -> str:  # pylint: disable=too-many-return-statements
    """Return a string naming the file type reported by :func:`os.stat`."""
    if stat.S_ISDIR(st.st_mode):
        return "directory"
    if stat.S_ISCHR(st.st_mode):  # pragma: no cover
        return "character special device file"
    if stat.S_ISBLK(st.st_mode):  # pragma: no cover
        return "block special device file"
    if stat.S_ISREG(st.st_mode):
        return "regular file"
    if stat.S_ISFIFO(st.st_mode):  # cover-not-win32
        return "FIFO (named pipe)"
    if stat.S_ISLNK(st.st_mode):  # cover-not-win32
        return "symbolic link"
    if stat.S_ISSOCK(st.st_mode):  # pragma: no cover
        return "socket"
    # Solaris
    if stat.S_ISDOOR(st.st_mode):  # pragma: no cover
        return "door"
    # Solaris?
    if stat.S_ISPORT(st.st_mode):  # pragma: no cover
        return "event port"
    # union/overlay file systems
    if stat.S_ISWHT(st.st_mode):  # pragma: no cover
        return "whiteout"
    raise ValueError(f"unknown filetype {st.st_mode:#o}")  # pragma: no cover

invalidchars = frozenset( '<>:"/\\|?*' + bytes(range(32)).decode('ASCII') )
invalidnames = frozenset(( 'CON', 'PRN', 'AUX', 'NUL',
    'COM0', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT0', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9' ))
def is_windows_filename_bad(fn :str) -> bool:
    """Check whether a Windows filename is invalid.

    Tests whether a filename contains invalid characters or has an invalid name, but
    does *not* check whether there are name collisions between filenames of differing case.

    Reference: https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file
    """
    return ( bool( set(fn).intersection(invalidchars) )  # invalid characters and names
        or fn.upper() in invalidnames
        # names are still invalid even if they have an extension
        or any( fn.upper().startswith(x+".") for x in invalidnames )
        # filenames shouldn't end on a space or period
        or fn[-1] in (' ', '.') )

@contextmanager
def open_out(filename :Optional[Filename] = None, mode='w', *, encoding='UTF-8', errors=None, newline=None):
    """This context manager either opens the file specified and provides its file object, or,
    if the filename is not specified or it is the string ``"-"``, ``sys.stdout`` is provided.

    *Please note* that the default encoding is UTF-8, which you can of course override with the ``encoding`` parameter."""
    if filename and filename != '-':
        with open(filename, mode, encoding=encoding, errors=errors, newline=newline) as fh:
            yield fh
    else:
        yield sys.stdout

@contextmanager
def replacer(file :Filename, *, binary :bool=False, encoding=None, errors=None, newline=None):
    """Replace a file by renaming a temporary file over the original.

    With this context manager, a temporary file is created in the same directory as the original file.
    The context manager gives you two file handles: the input file, and the output file, the latter
    being the temporary file. You can then read from the input file and write to the output file.
    When the context manager is exited, it will replace the input file with the temporary file.
    If an error occurs in the context manager, the temporary file is unlinked and the original file left unchanged.

    Depending on the OS and file system, the :func:`os.replace` used here *may* be an atomic operation.
    However, this function doesn't provide protection against multiple writers and is therefore
    intended for files with a single writer and multiple readers.
    Multiple writers will need to be coordinated with external locking mechanisms.
    """
    fname = Path(file).resolve(strict=True)
    if not fname.is_file():
        raise ValueError(f"not a regular file: {fname}")
    with fname.open(mode = 'rb' if binary else 'r', encoding=encoding, errors=errors, newline=newline) as infh:
        origmode = stat.S_IMODE( os.stat(infh.fileno()).st_mode )
        with NamedTemporaryFile( dir=fname.parent, prefix="."+fname.name+"_", delete=False,
                mode = 'wb' if binary else 'w', encoding=encoding, errors=errors, newline=newline) as tf:
            try:
                yield infh, tf
            except BaseException:
                tf.close()
                os.unlink(tf.name)
                raise
    # note because any exceptions are reraised above, we can only get here on success:
    try:
        os.chmod(tf.name, origmode)
    except NotImplementedError:  # pragma: no cover
        pass
    os.replace(tf.name, fname)

def replace_symlink(src :Filename, dst :Filename, *, missing_ok :bool=False):  # cover-only-posix
    """Attempt to atomically replace (or create) a symbolic link pointing to ``src`` named ``dst``.

    This function works by trying to choose a temporary filename for the link in the destination directory,
    and then replacing the target with that temporary link.

    Depending on the OS and file system, the :func:`os.replace` used here *may* be an atomic operation.
    However, the surrounding operations (e.g. checking if ``dst`` exists etc.) present a small
    chance for race conditions, so this function is primarily suited for situations with a single
    writer and multiple readers.
    Multiple writers will need to be coordinated with external locking mechanisms.

    :seealso: :func:`replace_link` can do the same, but using a temporary directory instead of
        a temporary file in the same directory as the target file.
    """
    if os.name != 'posix':  # cover-not-posix
        raise NotImplementedError("only available on POSIX systems")
    dst = Path(dst)  # DON'T Path.resolve() because that resolves symlinks
    try:
        dst.lstat()  # Path.exists() resolves symlinks
    except FileNotFoundError:
        if missing_ok:
            os.symlink(src, dst)
            return
        raise
    while True:
        tf = dst.parent / ( "."+dst.name+"_"+str(uuid.uuid4()) )
        try:
            os.symlink(src, tf)  # "Create a symbolic link pointing to src named dst."
            break  # this name was unused (highly likely)
        except FileExistsError:
            pass  # try again
    try:
        os.replace(tf, dst)
    except BaseException:
        os.unlink(tf)
        raise

def replace_link(src :Filename, dst :Filename, *, symbolic :bool=False):  # cover-only-posix
    """Attempt to atomically create or replace a hard or symbolic link pointing to ``src`` named ``dst``.

    This function works by creating the link in a new temporary directory first,
    thus offloading the responsibility for finding a fitting temporary name and
    cleanup to :class:`~tempfile.TemporaryDirectory`.

    Depending on the OS and file system, the :func:`os.replace` used here *may* be an atomic operation.
    However, this function doesn't provide protection against multiple writers and is therefore
    intended for files with a single writer and multiple readers.
    Multiple writers will need to be coordinated with external locking mechanisms.
    """
    if os.name != 'posix':  # cover-not-posix
        # Although in theory Python provides os.link and os.symlink on Windows, we don't support that here.
        raise NotImplementedError("only available on POSIX systems")
    # Reminder to self: DON'T Path.resolve() because that resolves symlinks
    with TemporaryDirectory(dir=Path(dst).parent) as td:
        tf = Path(td, Path(src).name)
        if symbolic:
            os.symlink(src, tf)  # "Create a symbolic link pointing to src named dst."
        else:
            os.link(src, tf)  # "Create a hard link pointing to src named dst."
        os.replace(tf, dst)

@contextmanager
def NamedTempFileDeleteLater(*args, **kwargs) -> Generator:  # pylint: disable=invalid-name  # cover-req-lt3.12
    """A :func:`~tempfile.NamedTemporaryFile` that is unlinked on context manager exit, not on close.

    On Python >=3.12, this simply calls :func:`tempfile.NamedTemporaryFile` with ``delete=True``
    and the new ``delete_on_close=False``."""
    tf = NamedTemporaryFile(*args, **kwargs, delete=False)  # type: ignore[call-overload]
    try:
        yield tf
    finally:
        os.unlink(tf.name)
NamedTempFileDeleteLater = ( partial(NamedTemporaryFile, delete_on_close=False, delete=True)  # pyright: ignore [reportCallIssue]
                            if sys.hexversion>=0x030C00B0 else NamedTempFileDeleteLater )  # type: ignore[assignment]

_perm_map :dict[bool, dict[int, int]] = {
    False: { 0: 0o444, S_IXUSR: 0o555, S_IWUSR: 0o644, S_IWUSR|S_IXUSR: 0o755 },
    True:  { 0: 0o444, S_IXUSR: 0o555, S_IWUSR: 0o664, S_IWUSR|S_IXUSR: 0o775 },
}
def simple_perms(st_mode :int, *, group_write :bool = False) -> tuple[int, int]:  # pragma: no cover
    """This function tests a file's permission bits to see if they are in a small set of "simple" permissions
    and suggests new permission bits if they are not.

    .. deprecated:: 0.5.0
        Use https://pypi.org/project/simple-perms/ instead.

    The set of "simple" permissions is (0o444, 0o555, 0o644, 0o755) or, when ``group_write`` is :obj:`True`, (0o444, 0o555, 0o664, 0o775).

    :param st_mode: The file's mode bits from :attr:`os.stat_result.st_mode`, such as returned by :func:`os.lstat` or :meth:`pathlib.Path.lstat`.
    :param group_write: When :obj:`True`, suggest that files / directories writable by the user should be writable by the group too.
    :return: A tuple consisting of the file's current permission and a suggested permission to use instead,
        based on the user's permission bits and whether the file is a directory or not.
        The two values may be equal indicating that no change is suggested.
        No changes are suggested for symbolic links.
    """
    warnings.warn("Use suggest_perms from package simple-perms instead", DeprecationWarning)
    return S_IMODE(st_mode), ( S_IMODE(st_mode) if S_ISLNK(st_mode)
                               else _perm_map[group_write][ ( st_mode|( S_IXUSR if S_ISDIR(st_mode) else 0 ) ) & (S_IWUSR|S_IXUSR) ] )

_T = TypeVar('_T')
def simple_cache(cache_file :Filename, *, verbose :bool=False) -> Callable[[Callable[[], _T]], Callable[[], _T]]:
    """A very basic caching decorator for functions that take no arguments, intended for caching data that is expensive to generate.

    On the first call of the function, its return value is saved to the specified file on disk via :mod:`pickle`,
    and on subsequent calls that file is loaded instead of calling the wrapped function.
    The original function can be called via the ``__wrapped__`` attribute on the outer function.
    Currently, the only way to clear the cache is by deleting the file.

    No file locking or other synchronization is performed, so this is likely not safe for threading or multiple processes.

    No type checking is performed on the data loaded from the file.

    .. warning::

        Please see the security warnings in the :mod:`pickle` documentation!

    For much more powerful caching and memoization, look at something like ``diskcache`` or similar modules.
    """
    cf = Path(cache_file)
    def decorator(orig_func :Callable[[], _T]) -> Callable[[], _T]:
        def wrapper() -> _T:
            data :_T
            if cf.exists():
                with cf.open('rb') as ifh:
                    data = pickle.load(ifh)
                if verbose:
                    print(f"Read {cf}", file=sys.stderr)
            else:
                data = orig_func()
                with cf.open('wb') as ofh:
                    pickle.dump(data, ofh)
                if verbose:
                    print(f"Wrote {cf}", file=sys.stderr)
            return data
        wrapper.__wrapped__ = orig_func  # type: ignore[attr-defined]
        return wrapper
    return decorator
